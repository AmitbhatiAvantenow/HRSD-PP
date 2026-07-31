from odoo import fields, models


class FlutterAttendanceSyncLog(models.Model):
    _name = 'flutterattendance.sync.log'
    _description = 'Offline Sync Log'
    _order = 'create_date desc'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    client_uuid = fields.Char(string='Client Reference', index=True, help="Client-generated id for the offline record")
    action_type = fields.Selection([
        ('check_in', 'Check-in'),
        ('check_out', 'Check-out'),
    ], required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('uploading', 'Uploading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], required=True, default='pending')
    attendance_id = fields.Many2one('flutterattendance.attendance')
    error_message = fields.Char()
    processed_at = fields.Datetime()
