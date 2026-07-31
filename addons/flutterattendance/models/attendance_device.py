from odoo import fields, models


class FlutterAttendanceDevice(models.Model):
    _name = 'flutterattendance.device'
    _description = 'Mobile Device'
    _rec_name = 'device_name'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    device_id = fields.Char(required=True, index=True, help="Unique device identifier reported by the app")
    device_name = fields.Char()
    os_version = fields.Char(string='OS Version')
    app_version = fields.Char()
    fcm_token = fields.Char(
        string='FCM Token',
        help="Reserved for future push-notification wiring; not currently used to send anything.",
    )
    last_login = fields.Datetime()
    last_sync = fields.Datetime()
    active = fields.Boolean(default=True)

    _device_employee_uniq = models.Constraint(
        'unique(employee_id, device_id)',
        'This device is already registered for this employee.',
    )
