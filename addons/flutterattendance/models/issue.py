import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class FlutterAttendanceIssue(models.Model):
    _name = 'flutterattendance.issue'
    _description = 'Employee-reported Issue (Report an Issue, mobile app)'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        required=True, copy=False, readonly=True, default=lambda self: _('New'),
        help="Ticket reference shown to the employee and HR, e.g. ISS-2026-0001.",
    )
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    description = fields.Text(required=True)
    photo = fields.Binary(attachment=True, help="Optional photo attached to the complaint.")
    video = fields.Binary(attachment=True, help="Optional video attached to the complaint.")
    video_filename = fields.Char()
    device_id = fields.Many2one('flutterattendance.device', string='Device')

    state = fields.Selection(
        [('new', 'New'), ('in_progress', 'In Progress'), ('resolved', 'Resolved')],
        default='new', required=True, index=True, tracking=True,
    )
    resolved_by = fields.Many2one('res.users')
    resolved_at = fields.Datetime()
    resolution_note = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('flutterattendance.issue') or _('New')
        records = super().create(vals_list)
        records._notify_issue_created()
        return records

    def write(self, vals):
        # Only mails for tickets that *become* resolved by this write, not
        # ones already resolved before it (e.g. an unrelated field edit on an
        # already-resolved ticket shouldn't re-notify the employee).
        newly_resolved = self.filtered(lambda r: r.state != 'resolved') if vals.get('state') == 'resolved' else self.browse()
        res = super().write(vals)
        if newly_resolved:
            newly_resolved._notify_issue_resolved()
        return res

    def action_start_progress(self):
        self.write({'state': 'in_progress'})

    def action_resolve(self):
        self.write({
            'state': 'resolved',
            'resolved_by': self.env.user.id,
            'resolved_at': fields.Datetime.now(),
        })

    def _notify_issue_created(self):
        try:
            self.env['flutterattendance.issue.mail'].sudo()._notify_created(self)
        except Exception:
            _logger.exception("flutterattendance: failed to notify developer team of new issue(s)")

    def _notify_issue_resolved(self):
        try:
            self.env['flutterattendance.issue.mail'].sudo()._notify_resolved(self)
        except Exception:
            _logger.exception("flutterattendance: failed to notify employee(s) of resolved issue(s)")
