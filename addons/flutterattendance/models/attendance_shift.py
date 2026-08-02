from datetime import timedelta

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
    break_start_time = fields.Float(help="e.g. 13.5 = 13:30. Leave at 0 for no scheduled break.")
    break_minutes = fields.Integer(default=0, help="Scheduled break duration in minutes")

    # Which calendar days this shift counts as a working day — drives both
    # the "Days Present / Total Working Days" and attendance % math, and
    # lets a company define e.g. a Tue-Sun shift instead of assuming
    # Mon-Fri is everyone's week.
    monday = fields.Boolean(default=True)
    tuesday = fields.Boolean(default=True)
    wednesday = fields.Boolean(default=True)
    thursday = fields.Boolean(default=True)
    friday = fields.Boolean(default=True)
    saturday = fields.Boolean(default=False)
    sunday = fields.Boolean(default=False)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    def is_working_day(self, date):
        """True if `date` (a date, not datetime) is a working day for this
        shift, per its Monday-Sunday flags."""
        self.ensure_one()
        flags = [self.monday, self.tuesday, self.wednesday, self.thursday, self.friday, self.saturday, self.sunday]
        return flags[date.weekday()]

    def working_days_between(self, date_from, date_to):
        """Count of this shift's configured working days in the inclusive
        [date_from, date_to] range — the shift-aware replacement for
        naively counting every calendar day (or assuming Mon-Fri)."""
        self.ensure_one()
        count = 0
        day = date_from
        while day <= date_to:
            if self.is_working_day(day):
                count += 1
            day += timedelta(days=1)
        return count
