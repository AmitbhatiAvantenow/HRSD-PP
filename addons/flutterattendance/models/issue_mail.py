import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .mail_mixin import BRAND_BLUE, BRAND_NAME, BRAND_SUPPORT_EMAIL, BRAND_TAGLINE, BRAND_WEBSITE, LOGO_CID, MARK_CID

_logger = logging.getLogger(__name__)

STATE_LABELS = {'new': 'New', 'in_progress': 'In Progress', 'resolved': 'Resolved'}
STATE_COLORS = {'new': '#d97706', 'in_progress': '#2451e0', 'resolved': '#16a34a'}
STATE_BG = {'new': '#fef3c7', 'in_progress': '#dbe6ff', 'resolved': '#dcfce7'}

DEFAULT_SUBJECTS = {
    'created': 'New Issue Raised - {issue_number}',
    'resolved': 'Your Issue Has Been Resolved - {issue_number}',
}


class FlutterAttendanceIssueMail(models.Model):
    _name = 'flutterattendance.issue.mail'
    _description = 'Issue Request Notification Mail'
    _inherit = ['flutterattendance.mail.mixin']
    _order = 'sequence, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    event_type = fields.Selection([
        ('created', 'New Issue Raised (notify Developer Team)'),
        ('resolved', 'Issue Resolved (notify the Employee who raised it)'),
    ], required=True, default='created',
        help="New Issue Raised fires the moment an employee submits a new issue via the mobile app "
             "(Issues Request), and goes to the To/Cc recipients configured below -- e.g. the "
             "developer team.\n"
             "Issue Resolved fires the moment an issue's Status is set to Resolved, and always goes "
             "to the employee who originally raised that ticket -- To (Employees)/To (Extra Emails) "
             "are ignored, since the recipient is that employee's own Work Email; Cc still applies.")

    to_employee_ids = fields.Many2many(
        'hr.employee', 'flutterattendance_issue_mail_to_employee_rel', 'mail_id', 'employee_id',
        string='To (Employees)', help="Uses each employee's Work Email.",
    )
    to_email_extra = fields.Char(string='To (Extra Emails)', help="Comma-separated email addresses.")
    cc_employee_ids = fields.Many2many(
        'hr.employee', 'flutterattendance_issue_mail_cc_employee_rel', 'mail_id', 'employee_id',
        string='Cc (Employees)', help="Uses each employee's Work Email.",
    )
    cc_email_extra = fields.Char(string='Cc (Extra Emails)', help="Comma-separated email addresses.")

    subject = fields.Char(
        required=True, default=lambda self: DEFAULT_SUBJECTS['created'],
        help="Use {issue_number} anywhere to insert the ticket reference, e.g. ISS-2026-0003.",
    )
    body_html = fields.Html(
        string='Mail Body', sanitize=False, required=True,
        default=lambda self: self._default_body_html(),
        help="Shown as the intro message above the issue's own details, which are added "
             "automatically below it. Use {issue_number} anywhere in the body too, if needed.",
    )

    last_sent_at = fields.Datetime(readonly=True, copy=False)
    last_sent_status = fields.Char(readonly=True, copy=False)

    @api.model
    def _default_body_html(self, event_type='created'):
        if event_type == 'resolved':
            return (
                "<p>Good news -- the issue you reported has just been marked as resolved.</p>"
                "<p>Details are below. Reply here or raise a new ticket if anything still needs "
                "attention.</p>"
            )
        return (
            "<p>A new issue has just been raised by an employee via the mobile app. Details are "
            "below.</p>"
        )

    @api.onchange('event_type')
    def _onchange_event_type(self):
        default_created = self._default_body_html('created')
        default_resolved = self._default_body_html('resolved')
        if str(self.body_html or '') in (default_created, default_resolved):
            self.body_html = self._default_body_html(self.event_type)
        if self.subject in (DEFAULT_SUBJECTS['created'], DEFAULT_SUBJECTS['resolved']):
            self.subject = DEFAULT_SUBJECTS[self.event_type]

    @api.model
    def _notify_created(self, issues):
        configs = self.search([('active', '=', True), ('event_type', '=', 'created')])
        for issue in issues:
            for config in configs:
                try:
                    config._send_for_issue(issue)
                except Exception:
                    _logger.exception(
                        "flutterattendance: failed to send issue-created mail (%s) for %s",
                        config.name, issue.name)

    @api.model
    def _notify_resolved(self, issues):
        configs = self.search([('active', '=', True), ('event_type', '=', 'resolved')])
        for issue in issues:
            for config in configs:
                try:
                    config._send_for_issue(issue)
                except Exception:
                    _logger.exception(
                        "flutterattendance: failed to send issue-resolved mail (%s) for %s",
                        config.name, issue.name)

    def action_send_test(self):
        self.ensure_one()
        issue = self.env['flutterattendance.issue'].search([], limit=1, order='id desc')
        if not issue:
            raise UserError(_("There are no issues yet to build a test mail from -- raise one first."))
        to_emails = [self.env.user.email] if self.env.user.email else []
        if not to_emails:
            raise UserError(_("Your own user has no email address to send the test to."))
        self._send_for_issue(issue, override_to=to_emails, test=True)

    def _send_for_issue(self, issue, override_to=None, test=False):
        self.ensure_one()
        if override_to:
            to_emails = override_to
        elif self.event_type == 'resolved':
            to_emails = [issue.employee_id.work_email] if issue.employee_id.work_email else []
        else:
            to_emails = self._get_emails(self.to_employee_ids, self.to_email_extra)
        cc_emails = [] if test else self._get_emails(self.cc_employee_ids, self.cc_email_extra)

        if not to_emails:
            _logger.warning(
                "flutterattendance: issue mail config %s has no recipient for %s; skipping",
                self.name, issue.name)
            if not test:
                self.last_sent_status = f'Skipped for {issue.name}: no recipient configured'
            return

        greeting_name = issue.employee_id.name if self.event_type == 'resolved' else 'Team'
        subject = (self.subject or DEFAULT_SUBJECTS[self.event_type]).replace('{issue_number}', issue.name or '')
        if test:
            subject = '[TEST] ' + subject
        body_final = self._render_issue_email_html(issue, greeting_name)

        msg = self._build_mime_message(
            subject=subject, html_body=body_final, to_emails=to_emails, cc_emails=cc_emails)
        self.env['ir.mail_server'].sudo().send_email(msg)
        self._log_sent_mail(subject, body_final, to_emails, cc_emails)

        if not test:
            self.write({
                'last_sent_at': fields.Datetime.now(),
                'last_sent_status': f'Sent for {issue.name} at {fields.Datetime.now()}',
            })

    def _render_issue_email_html(self, issue, greeting_name):
        self.ensure_one()
        tz_name = self.env.company.partner_id.tz or 'Asia/Kolkata'
        ctx_self = self.with_context(tz=tz_name)

        submitted_local = (
            fields.Datetime.context_timestamp(ctx_self, issue.create_date) if issue.create_date else None)
        rows = [
            ('Ticket', issue.name or ''),
            ('Employee', issue.employee_id.name or ''),
            ('Device', issue.device_id.display_name or '-'),
            ('Submitted On', submitted_local.strftime('%d %b %Y, %I:%M %p') if submitted_local else '-'),
        ]
        if issue.state == 'resolved':
            resolved_local = (
                fields.Datetime.context_timestamp(ctx_self, issue.resolved_at) if issue.resolved_at else None)
            rows += [
                ('Resolved By', issue.resolved_by.name or '-'),
                ('Resolved At', resolved_local.strftime('%d %b %Y, %I:%M %p') if resolved_local else '-'),
                ('Resolution Note', issue.resolution_note or '-'),
            ]

        rows_html = ''.join(f"""
                <tr>
                    <td style="padding:10px 16px;border-bottom:1px solid #eef1f6;color:#64748b;font-size:12px;font-weight:600;white-space:nowrap;">{label}</td>
                    <td style="padding:10px 16px;border-bottom:1px solid #eef1f6;color:#0f172a;font-size:13px;">{value}</td>
                </tr>""" for label, value in rows)

        description_html = (issue.description or '').replace('\n', '<br/>')

        attachment_names = []
        if issue.photo:
            attachment_names.append('a photo')
        if issue.video:
            attachment_names.append('a video')
        attachments_block = ''
        if attachment_names:
            attachments_line = f"This ticket also has {' and '.join(attachment_names)} attached -- open it in the system to view."
            attachments_block = f"""
            <div style="padding:12px 20px;background:#f8fafc;font-size:12px;color:#64748b;border-top:1px solid #eef1f6;">
                {attachments_line}
            </div>"""

        intro_html = str(self.body_html or '').replace('{issue_number}', issue.name or '')
        state_label = STATE_LABELS.get(issue.state, issue.state or '-')
        color = STATE_COLORS.get(issue.state, '#64748b')
        bg = STATE_BG.get(issue.state, '#f1f5f9')

        return f"""
<div style="max-width:640px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e5e9f2;">
    <div style="height:4px;background:{BRAND_BLUE};line-height:4px;font-size:0;">&nbsp;</div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
        <tr><td style="padding:24px 28px;">
            <img src="cid:{LOGO_CID}" alt="{BRAND_NAME}" style="height:34px;display:block;border:0;"/>
        </td></tr>
    </table>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fc;">
        <tr><td style="padding:0 28px 26px;">
            <div style="font-size:19px;color:#0f172a;">Hi <span style="color:{BRAND_BLUE};font-weight:700;">{greeting_name}</span>,</div>
            <div style="margin-top:12px;font-size:14px;line-height:1.7;color:#334155;">{intro_html}</div>
        </td></tr>
    </table>

    <div style="padding:0 24px 24px;background:#f3f6fc;">
        <div style="border-radius:14px;overflow:hidden;border:1px solid #e2e8f0;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{BRAND_BLUE};">
                <tr>
                    <td style="padding:18px 22px;vertical-align:middle;">
                        <div style="font-size:16px;font-weight:700;color:#ffffff;">{issue.name}</div>
                        <div style="font-size:12px;color:#dbe6ff;margin-top:2px;">Issue Request</div>
                    </td>
                    <td style="padding:18px 22px;text-align:right;vertical-align:middle;">
                        <span style="display:inline-block;padding:4px 12px;border-radius:12px;background-color:{bg};color:{color};font-size:12px;font-weight:700;">&#9679;&nbsp;{state_label}</span>
                    </td>
                </tr>
            </table>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-collapse:collapse;">
                {rows_html}
            </table>

            <div style="padding:14px 20px;border-top:1px solid #eef1f6;">
                <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:6px;">Description</div>
                <div style="font-size:13px;color:#0f172a;line-height:1.6;">{description_html}</div>
            </div>
            {attachments_block}
        </div>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-top:1px solid #eef1f6;">
        <tr>
            <td style="padding:22px 28px;vertical-align:middle;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding-right:12px;vertical-align:middle;">
                            <img src="cid:{MARK_CID}" alt="" style="width:38px;height:38px;border-radius:50%;display:block;border:0;"/>
                        </td>
                        <td style="vertical-align:middle;">
                            <div style="font-size:12px;color:#334155;">Regards,</div>
                            <div style="font-size:14px;font-weight:700;color:{BRAND_BLUE};">{BRAND_NAME} Team</div>
                            <div style="font-size:11px;color:#94a3b8;">{BRAND_TAGLINE}</div>
                        </td>
                    </tr>
                </table>
            </td>
            <td style="padding:22px 28px;text-align:right;vertical-align:middle;">
                <div style="font-size:12px;color:#334155;">&#127760;&nbsp; {BRAND_WEBSITE}</div>
                <div style="font-size:12px;color:#334155;margin-top:6px;">&#9993;&nbsp; {BRAND_SUPPORT_EMAIL}</div>
            </td>
        </tr>
    </table>
</div>"""
