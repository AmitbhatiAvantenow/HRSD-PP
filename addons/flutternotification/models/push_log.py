from odoo import fields, models


class FlutterNotificationPushLog(models.Model):
    _name = 'flutternotification.push_log'
    _description = 'Push Notification Delivery Log'
    _order = 'create_date desc'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    device_id = fields.Many2one('flutterattendance.device', ondelete='set null')
    # Nullable: 'test' pushes (Settings > Send Test Push) have no attendance
    # session behind them.
    attendance_id = fields.Many2one('flutterattendance.attendance', ondelete='cascade', index=True)
    kind = fields.Selection([
        ('backup_checkout_reminder', 'Backup Check-out Reminder'),
        ('test', 'Test'),
    ], required=True, default='test')
    platform = fields.Selection([('android', 'Android'), ('ios', 'iOS')])
    state = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped_no_token', 'Skipped (No Token)'),
    ], required=True, index=True)
    provider_status_code = fields.Integer()
    provider_response = fields.Text()
