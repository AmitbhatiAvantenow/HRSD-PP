import io
import logging
from datetime import timedelta

import pytz
import xlsxwriter

from odoo import api, fields, models

from .mail_mixin import BRAND_BLUE, BRAND_NAME, BRAND_SUPPORT_EMAIL, BRAND_TAGLINE, BRAND_WEBSITE, LOGO_CID, MARK_CID

_logger = logging.getLogger(__name__)

STATUS_COLORS = {
    'present': '#16a34a',
    'late': '#d97706',
    'half_day': '#d97706',
    'absent': '#dc2626',
    'missed_checkout': '#dc2626',
}
# Solid tint per status, not an alpha-blended hex, since Outlook's rendering
# engine drops the alpha channel unpredictably (an 8-digit hex or rgba()
# background can silently become fully transparent).
STATUS_BG = {
    'present': '#dcfce7',
    'late': '#fef3c7',
    'half_day': '#fef3c7',
    'absent': '#fee2e2',
    'missed_checkout': '#fee2e2',
}


def _tz_get(self):
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class FlutterAttendanceMail(models.Model):
    _name = 'flutterattendance.attendance.mail'
    _description = 'End-of-Day Attendance Mail'
    _inherit = ['flutterattendance.mail.mixin']
    _order = 'sequence, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    mail_type = fields.Selection([
        ('summary', 'Management Summary'),
        ('employee', 'Employee Daily Summary'),
    ], required=True, default='summary',
        help="Management Summary sends one combined mail (every employee's check-in/out) to the "
             "To/Cc recipients configured below.\n"
             "Employee Daily Summary instead sends each employee who has an attendance record that "
             "day their own individual mail, containing only their own record -- To (Employees)/To "
             "(Extra Emails) are ignored, since the recipient is always that employee's own Work "
             "Email; Cc still applies to every one of those mails if set.")

    send_time = fields.Float(
        string='Send At', default=18.1667, required=True,
        help="24-hour local time (in the Timezone below) this mail goes out, e.g. 18:10 = 18.17. "
             "The scheduled action checks every few minutes, so this is the earliest moment it can "
             "fire that day, not an exact-to-the-second trigger.",
    )
    report_day = fields.Selection([
        ('today', 'Today'),
        ('yesterday', 'Previous Day'),
    ], string='Attendance Date', default='today', required=True,
        help="Which day's attendance this mail reports on. 'Today' includes whatever check-ins/"
             "check-outs have happened so far as of Send At, which may still be incomplete for "
             "anyone not yet checked out. 'Previous Day' reports the last full day instead, e.g. "
             "a mail sent on 18 Aug covers 17 Aug's attendance for everyone.",
    )
    tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self.env.company.partner_id.tz or 'Asia/Kolkata',
    )
    skip_saturday = fields.Boolean(
        string='Skip Saturday', default=True,
        help="Don't send automatically on Saturday. Only affects the daily schedule -- "
             "Send Now/Send Test Mail still work on any day.",
    )
    skip_sunday = fields.Boolean(
        string='Skip Sunday', default=True,
        help="Don't send automatically on Sunday. Only affects the daily schedule -- "
             "Send Now/Send Test Mail still work on any day.",
    )

    to_employee_ids = fields.Many2many(
        'hr.employee', 'flutterattendance_mail_to_employee_rel', 'mail_id', 'employee_id',
        string='To (Employees)', help="Uses each employee's Work Email.",
    )
    to_email_extra = fields.Char(string='To (Extra Emails)', help="Comma-separated email addresses.")
    cc_employee_ids = fields.Many2many(
        'hr.employee', 'flutterattendance_mail_cc_employee_rel', 'mail_id', 'employee_id',
        string='Cc (Employees)', help="Uses each employee's Work Email.",
    )
    cc_email_extra = fields.Char(string='Cc (Extra Emails)', help="Comma-separated email addresses.")

    subject = fields.Char(
        required=True, default='End of Day Attendance Report - {date}',
        help="Use {date} anywhere in the subject to insert the attendance date.",
    )
    body_html = fields.Html(
        string='Mail Body', sanitize=False, required=True,
        default=lambda self: self._default_body_html(),
        help="Shown as the intro message right under the greeting. The branded attendance summary "
             "table, Excel note and footer are added automatically below it.",
    )
    include_excel = fields.Boolean(
        string='Attach Excel Export', default=True,
        help="Attach that day's Mobile Attendance records as an .xlsx file, matching the standard "
             "list export (Employee, Check In/Out, Working Hours, Distance, Status, Comment).",
    )

    last_sent_date = fields.Date(readonly=True, copy=False)
    last_sent_status = fields.Char(readonly=True, copy=False)

    @api.model
    def _default_body_html(self, mail_type='summary', report_day='today'):
        day_label = "today's" if report_day == 'today' else "yesterday's"
        if mail_type == 'employee':
            return (
                f"<p>Here's your check-in / check-out summary for {day_label}.</p>"
                "<p>The full detail (GPS, distance, your comments) is attached as an Excel export.</p>"
            )
        return (
            f"<p>Please find below {day_label} check-in / check-out summary for all employees.</p>"
            "<p>The full detail (GPS, distance, comments) is attached as an Excel export.</p>"
        )

    @api.onchange('mail_type', 'report_day')
    def _onchange_mail_type(self):
        all_defaults = {
            self._default_body_html(mail_type, report_day)
            for mail_type in ('summary', 'employee') for report_day in ('today', 'yesterday')
        }
        if str(self.body_html or '') in all_defaults:
            self.body_html = self._default_body_html(self.mail_type, self.report_day)

    @api.model
    def _cron_send_daily_attendance_mail(self):
        for config in self.search([('active', '=', True)]):
            try:
                config._send_if_due()
            except Exception:
                _logger.exception(
                    "flutterattendance: failed to send end-of-day attendance mail for %s", config.name)

    def _send_if_due(self):
        self.ensure_one()
        tz_name = self.tz or 'Asia/Kolkata'
        now_local = fields.Datetime.context_timestamp(self.with_context(tz=tz_name), fields.Datetime.now())
        today = now_local.date()
        if self.last_sent_date == today:
            return
        # Monday=0 ... Saturday=5, Sunday=6. Checked against the mail's own
        # Timezone, same as the send-time window below, so a Send At near
        # midnight doesn't land on the wrong side of the weekend boundary.
        weekday = now_local.weekday()
        if (weekday == 5 and self.skip_saturday) or (weekday == 6 and self.skip_sunday):
            return
        current_minutes = now_local.hour * 60 + now_local.minute
        target_minutes = round(self.send_time * 60)
        # Window big enough to absorb delay/downtime in the scheduled action's own
        # polling interval, but capped so it doesn't fire hours late either.
        if not (target_minutes <= current_minutes < target_minutes + 20):
            return
        self._send()

    def action_send_now(self):
        for config in self:
            config._send()

    def action_send_test(self):
        for config in self:
            config._send(test=True)

    def _greeting_name(self):
        self.ensure_one()
        names = self.to_employee_ids.mapped('name')
        return names[0] if len(names) == 1 else 'Team'

    def _get_send_date(self):
        """The actual calendar day (in the mail's own Timezone) this send is
        happening on -- used only for the last_sent_date dedup guard, never
        for picking which attendance records to report on."""
        self.ensure_one()
        tz_name = self.tz or 'Asia/Kolkata'
        return fields.Datetime.context_timestamp(
            self.with_context(tz=tz_name), fields.Datetime.now()).date()

    def _format_sent_status(self, prefix='Sent'):
        """'<prefix> at YYYY-MM-DD HH:MM:SS <Timezone>', in the mail's own
        Timezone rather than the raw server/UTC clock -- fields.Datetime.now()
        alone reads as wrong-looking (e.g. hours off from Send At) once you
        compare it against IST by eye."""
        self.ensure_one()
        tz_name = self.tz or 'Asia/Kolkata'
        now_local = fields.Datetime.context_timestamp(self.with_context(tz=tz_name), fields.Datetime.now())
        return f"{prefix} at {now_local.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"

    def _get_today(self):
        """The calendar day this mail's report covers -- the current day, or the
        previous full day when Attendance Date is set to 'Previous Day' (e.g. a
        CEO/management mail sent each evening that should always show a complete
        day, not whoever hasn't checked out yet)."""
        self.ensure_one()
        today = self._get_send_date()
        if self.report_day == 'yesterday':
            return today - timedelta(days=1)
        return today

    def _send(self, test=False):
        self.ensure_one()
        today = self._get_today()
        if self.mail_type == 'employee':
            self._send_employee_batch(today, test=test)
        else:
            self._send_summary(today, test=test)

    def _today_records(self, today):
        Attendance = self.env['flutterattendance.attendance'].sudo()
        domain = [('attendance_date', '=', today)]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        return Attendance.search(domain, order='employee_id')

    def _send_summary(self, today, test=False):
        self.ensure_one()
        records = self._today_records(today)

        if test:
            to_emails = [self.env.user.email] if self.env.user.email else []
            cc_emails = []
            greeting_name = self.env.user.name
        else:
            to_emails = self._get_emails(self.to_employee_ids, self.to_email_extra)
            cc_emails = self._get_emails(self.cc_employee_ids, self.cc_email_extra)
            greeting_name = self._greeting_name()

        if not to_emails:
            _logger.warning("flutterattendance: mail config %s has no recipients; skipping send", self.name)
            if not test:
                self.last_sent_status = 'Skipped: no recipients configured'
            return

        self._dispatch_mail(records, today, greeting_name, to_emails, cc_emails, test=test)

        if not test:
            self.write({
                'last_sent_date': self._get_send_date(),
                'last_sent_status': self._format_sent_status(),
            })

    def _send_employee_batch(self, today, test=False):
        self.ensure_one()
        by_employee = {}
        for rec in self._today_records(today):
            by_employee.setdefault(rec.employee_id, self.env['flutterattendance.attendance'])
            by_employee[rec.employee_id] |= rec

        if test:
            employee = self.env.user.employee_id
            if employee not in by_employee:
                employee = next(iter(by_employee), employee)
            to_emails = [self.env.user.email] if self.env.user.email else []
            if not to_emails:
                _logger.warning("flutterattendance: mail config %s has no test recipient (current user has no email)", self.name)
                return
            records = by_employee.get(employee, self.env['flutterattendance.attendance'])
            self._dispatch_mail(records, today, employee.name if employee else 'Team', to_emails, [], test=True)
            return

        if not by_employee:
            self.last_sent_status = 'Skipped: no attendance records today'
            return

        cc_emails = self._get_emails(self.cc_employee_ids, self.cc_email_extra)
        sent, skipped = 0, 0
        for employee, records in by_employee.items():
            email = employee.work_email
            if not email:
                skipped += 1
                _logger.warning(
                    "flutterattendance: mail config %s skipped employee %s: no Work Email set",
                    self.name, employee.name)
                continue
            self._dispatch_mail(records, today, employee.name, [email], cc_emails, test=False)
            sent += 1

        status = self._format_sent_status(f'Sent to {sent} employee(s)')
        if skipped:
            status += f' ({skipped} skipped: no Work Email)'
        self.write({'last_sent_date': self._get_send_date(), 'last_sent_status': status})

    def _dispatch_mail(self, records, today, greeting_name, to_emails, cc_emails, test=False):
        """Builds and sends one branded email for the given records/recipients,
        and logs an already-'sent' mail.mail record for audit history."""
        self.ensure_one()
        body_final = self._render_email_html(records, today, greeting_name)

        subject = (self.subject or 'End of Day Attendance Report - {date}').replace(
            '{date}', today.strftime('%d %b %Y'))
        if test:
            subject = '[TEST] ' + subject

        xlsx_data = self._build_xlsx(records) if self.include_excel else None
        xlsx_filename = self._xlsx_filename(today, greeting_name) if xlsx_data else None
        attachments = [{
            'filename': xlsx_filename, 'data': xlsx_data, 'maintype': 'application',
            'subtype': 'vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }] if xlsx_data else None

        msg = self._build_mime_message(
            subject=subject, html_body=body_final, to_emails=to_emails, cc_emails=cc_emails,
            attachments=attachments,
        )
        self.env['ir.mail_server'].sudo().send_email(msg)
        self._log_sent_mail(subject, body_final, to_emails, cc_emails, attachments=attachments)

    def _xlsx_filename(self, today, greeting_name):
        """{Employee}_{date}.xlsx for an Employee Daily Summary mail (one
        employee's own records), {date}_attendance.xlsx for a Management
        Summary mail (everyone's records)."""
        self.ensure_one()
        date_str = today.strftime('%Y-%m-%d')
        if self.mail_type == 'employee':
            safe_name = (greeting_name or 'Employee').strip().replace('/', '-').replace(' ', '_')
            return f"{safe_name}_{date_str}.xlsx"
        return f"{date_str}_attendance.xlsx"

    def _render_email_html(self, records, today, greeting_name):
        """Full branded HTML email: header (logo + date), greeting/intro, a
        blue summary banner + attendance table card, and a footer. Built with
        <table> layout and inline styles throughout (not flexbox/grid, no
        external stylesheet) since that's what actually renders consistently
        across mail clients, unlike a regular web page."""
        self.ensure_one()
        tz_name = self.tz or 'Asia/Kolkata'

        rows = []
        for rec in records.sorted(key=lambda r: r.employee_id.name or ''):
            rec_tz = rec.with_context(tz=tz_name)
            check_in = fields.Datetime.context_timestamp(rec_tz, rec.check_in_time) if rec.check_in_time else None
            check_out = fields.Datetime.context_timestamp(rec_tz, rec.check_out_time) if rec.check_out_time else None
            color = STATUS_COLORS.get(rec.status, '#64748b')
            bg = STATUS_BG.get(rec.status, '#f1f5f9')
            status_label = (rec.status or '').replace('_', ' ').title() or '-'
            rows.append(f"""
                <tr>
                    <td style="padding:14px 16px;border-bottom:1px solid #eef1f6;color:#0f172a;font-size:13px;font-weight:600;">{rec.employee_id.name or ''}</td>
                    <td style="padding:14px 16px;border-bottom:1px solid #eef1f6;color:#475569;font-size:13px;">{check_in.strftime('%I:%M %p') if check_in else '-'}</td>
                    <td style="padding:14px 16px;border-bottom:1px solid #eef1f6;color:#475569;font-size:13px;">{check_out.strftime('%I:%M %p') if check_out else '-'}</td>
                    <td style="padding:14px 16px;border-bottom:1px solid #eef1f6;color:#475569;font-size:13px;">{rec.working_hours:.2f} h</td>
                    <td style="padding:14px 16px;border-bottom:1px solid #eef1f6;">
                        <span style="display:inline-block;padding:4px 12px;border-radius:12px;background-color:{bg};color:{color};font-size:12px;font-weight:700;">&#9679;&nbsp;{status_label}</span>
                    </td>
                </tr>""")
        rows_html = ''.join(rows) if rows else """
                <tr><td colspan="5" style="padding:22px 16px;color:#94a3b8;font-size:13px;text-align:center;">No attendance recorded today.</td></tr>"""

        intro_html = str(self.body_html or '')
        excel_note = (
            "Full detail (GPS, distance, comments) is attached as an Excel export."
            if self.include_excel else
            "Excel export attachment is disabled for this mail."
        )

        date_label = today.strftime('%d %b %Y')
        weekday_label = today.strftime('%A')
        banner_title = 'Your End of Day Attendance' if self.mail_type == 'employee' else 'End of Day Attendance Summary'
        badge_label = 'Record Today' if self.mail_type == 'employee' else 'Total Records'

        return f"""
<div style="max-width:660px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e5e9f2;">
    <div style="height:4px;background:{BRAND_BLUE};line-height:4px;font-size:0;">&nbsp;</div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
        <tr>
            <td style="padding:24px 28px;vertical-align:middle;">
                <img src="cid:{LOGO_CID}" alt="{BRAND_NAME}" style="height:34px;display:block;border:0;"/>
            </td>
            <td style="padding:24px 28px;text-align:right;vertical-align:middle;">
                <table role="presentation" cellpadding="0" cellspacing="0" style="display:inline-table;background:#eef3ff;border-radius:10px;">
                    <tr>
                        <td style="padding:8px 16px;text-align:left;">
                            <div style="font-size:13px;font-weight:700;color:#0f172a;white-space:nowrap;">&#128197;&nbsp; {date_label}</div>
                            <div style="font-size:11px;color:#64748b;">{weekday_label}</div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fc;">
        <tr>
            <td style="padding:26px 28px 30px;vertical-align:top;">
                <div style="font-size:19px;color:#0f172a;">Hi <span style="color:{BRAND_BLUE};font-weight:700;">{greeting_name}</span>,</div>
                <div style="margin-top:12px;font-size:14px;line-height:1.7;color:#334155;">{intro_html}</div>
            </td>
        </tr>
    </table>

    <div style="padding:0 24px 24px;background:#f3f6fc;">
        <div style="border-radius:14px;overflow:hidden;border:1px solid #e2e8f0;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{BRAND_BLUE};">
                <tr>
                    <td style="padding:20px 22px;vertical-align:middle;">
                        <table role="presentation" cellpadding="0" cellspacing="0">
                            <tr>
                                <td style="padding-right:14px;">
                                    <div style="width:42px;height:42px;border-radius:50%;background:#ffffff;text-align:center;line-height:42px;font-size:18px;">&#128337;</div>
                                </td>
                                <td>
                                    <div style="font-size:16px;font-weight:700;color:#ffffff;">{banner_title}</div>
                                    <div style="font-size:12px;color:#dbe6ff;margin-top:2px;">{date_label}</div>
                                </td>
                            </tr>
                        </table>
                    </td>
                    <td style="padding:20px 22px;text-align:right;vertical-align:middle;">
                        <table role="presentation" cellpadding="0" cellspacing="0" style="display:inline-table;background-color:#3f6bef;border-radius:10px;">
                            <tr>
                                <td style="padding:8px 14px;">
                                    <div style="color:#ffffff;font-weight:700;font-size:15px;">&#128101; {len(records)}</div>
                                    <div style="color:#dbe6ff;font-size:10px;">{badge_label}</div>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-collapse:collapse;">
                <tr style="background:#f8fafc;">
                    <th style="text-align:left;padding:12px 16px;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">&#128100; Employee</th>
                    <th style="text-align:left;padding:12px 16px;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">&#8594; Check In</th>
                    <th style="text-align:left;padding:12px 16px;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">&#8592; Check Out</th>
                    <th style="text-align:left;padding:12px 16px;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">&#9201; Working Hours</th>
                    <th style="text-align:left;padding:12px 16px;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">&#9873; Status</th>
                </tr>
                {rows_html}
            </table>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fc;">
                <tr>
                    <td style="padding:14px 22px;font-size:12px;color:#64748b;">
                        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
                            <td style="padding-right:8px;vertical-align:middle;">
                                <div style="width:20px;height:20px;border-radius:4px;background:#16a34a;color:#ffffff;font-size:10px;font-weight:700;text-align:center;line-height:20px;">X</div>
                            </td>
                            <td style="vertical-align:middle;">{excel_note}</td>
                        </tr></table>
                    </td>
                </tr>
            </table>
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

    def _build_xlsx(self, records):
        self.ensure_one()
        tz_name = self.tz or 'Asia/Kolkata'
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Mobile Attendance')

        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#0f172a', 'font_color': 'white', 'border': 1,
        })
        cell_format = workbook.add_format({'border': 1})

        headers = ['Employee', 'Attendance Date', 'Check In Time', 'Check Out Time',
                    'Working Hours', 'Distance (km)', 'Status', 'Missed Checkout', 'Comment']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 20)

        for row, rec in enumerate(records, start=1):
            rec_tz = rec.with_context(tz=tz_name)
            check_in = fields.Datetime.context_timestamp(rec_tz, rec.check_in_time) if rec.check_in_time else None
            check_out = fields.Datetime.context_timestamp(rec_tz, rec.check_out_time) if rec.check_out_time else None
            sheet.write(row, 0, rec.employee_id.name or '', cell_format)
            sheet.write(row, 1, str(rec.attendance_date or ''), cell_format)
            sheet.write(row, 2, check_in.strftime('%Y-%m-%d %H:%M') if check_in else '', cell_format)
            sheet.write(row, 3, check_out.strftime('%Y-%m-%d %H:%M') if check_out else '', cell_format)
            sheet.write(row, 4, rec.working_hours, cell_format)
            sheet.write(row, 5, rec.distance_km, cell_format)
            sheet.write(row, 6, (rec.status or '').replace('_', ' ').title(), cell_format)
            sheet.write(row, 7, 'Yes' if rec.missed_checkout else 'No', cell_format)
            sheet.write(row, 8, rec.remarks or '', cell_format)

        workbook.close()
        return output.getvalue()
