from odoo import fields, models


class FlutterAttendanceShift(models.Model):
    _name = 'flutterattendance.shift'
    _description = 'Attendance Shift'

    name = fields.Char(required=True)
    start_time = fields.Float(required=True, default=9.5, help="Shift start time, e.g. 9.5 = 09:30")
    end_time = fields.Float(required=True, default=18.5, help="Shift end time, e.g. 18.5 = 18:30")
    grace_minutes = fields.Integer(default=10, help="Minutes of grace period before a check-in counts as late")
    half_day_hours = fields.Float(default=4.0, help="Minimum worked hours to avoid being marked half-day")
    full_day_hours = fields.Float(default=8.0, help="Expected worked hours for a full day; extra counts as overtime")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
