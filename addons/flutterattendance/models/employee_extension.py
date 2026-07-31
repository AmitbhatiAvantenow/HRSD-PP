from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _default_attendance_shift(self):
        return self.env.ref('flutterattendance.shift_general', raise_if_not_found=False)

    attendance_shift_id = fields.Many2one(
        'flutterattendance.shift',
        string='Attendance Shift',
        default=_default_attendance_shift,
    )
    attendance_device_ids = fields.One2many('flutterattendance.device', 'employee_id', string='Mobile Devices')
