from datetime import timedelta

from odoo import api, fields, models


class FlutterAttendance(models.Model):
    _name = 'flutterattendance.attendance'
    _description = 'Mobile Attendance'
    _order = 'check_in_time desc'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    attendance_date = fields.Date(required=True, default=fields.Date.context_today, index=True)

    check_in_time = fields.Datetime(required=True)
    check_out_time = fields.Datetime()

    working_hours = fields.Float(compute='_compute_summary', store=True)
    distance_km = fields.Float(compute='_compute_summary', store=True, string='Distance (km)', digits=(10, 3))
    late_minutes = fields.Float(compute='_compute_summary', store=True)
    overtime_hours = fields.Float(compute='_compute_summary', store=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
    ], compute='_compute_summary', store=True)
    remarks = fields.Char()

    # Check-in
    checkin_latitude = fields.Float(digits=(10, 7))
    checkin_longitude = fields.Float(digits=(10, 7))
    checkin_address = fields.Char()
    checkin_accuracy = fields.Float(help="GPS accuracy in meters")
    checkin_photo = fields.Binary(attachment=True)
    device_id = fields.Many2one('flutterattendance.device', string='Device')
    checkin_battery = fields.Float(string='Check-in Battery %')
    checkin_network = fields.Char(string='Check-in Network', help="e.g. wifi, 4g, 5g")
    checkin_internet = fields.Boolean(default=True, string='Online at Check-in')
    checkin_ip_address = fields.Char(string='Check-in IP Address')
    checkin_created_at = fields.Datetime(
        default=fields.Datetime.now,
        help="When the record actually reached the server (may lag check_in_time for offline-synced records).",
    )
    checkin_face_similarity = fields.Float(help="Cosine similarity vs. the employee's registered face, 0-1.")
    checkin_face_verified = fields.Boolean(
        help="True if face_engine matched automatically; False if this only exists because HR approved it "
             "after face_recognition failed (see flutterattendance.face.approval).",
    )

    # Check-out
    checkout_latitude = fields.Float(digits=(10, 7))
    checkout_longitude = fields.Float(digits=(10, 7))
    checkout_address = fields.Char()
    checkout_accuracy = fields.Float(help="GPS accuracy in meters")
    checkout_photo = fields.Binary(attachment=True)
    checkout_created_at = fields.Datetime()
    checkout_face_similarity = fields.Float(help="Cosine similarity vs. the employee's registered face, 0-1.")
    checkout_face_verified = fields.Boolean(
        help="True if face_engine matched automatically; False if this only exists because HR approved it "
             "after face_recognition failed (see flutterattendance.face.approval).",
    )

    _checkout_after_checkin = models.Constraint(
        'CHECK(check_out_time IS NULL OR check_out_time >= check_in_time)',
        'Check-out time cannot be before check-in time.',
    )

    @api.model
    def _find_open_session(self, employee):
        return self.search([
            ('employee_id', '=', employee.id),
            ('check_out_time', '=', False),
        ], limit=1, order='check_in_time desc')

    @api.depends('check_in_time', 'check_out_time',
                 'checkin_latitude', 'checkin_longitude', 'checkout_latitude', 'checkout_longitude')
    def _compute_summary(self):
        for rec in self:
            shift = rec.employee_id.attendance_shift_id

            if rec.check_in_time and rec.check_out_time:
                delta = rec.check_out_time - rec.check_in_time
                rec.working_hours = round(delta.total_seconds() / 3600.0, 2)
            else:
                rec.working_hours = 0.0

            rec.distance_km = rec._haversine_km()
            rec.late_minutes = rec._compute_late_minutes(shift)

            full_day_hours = shift.full_day_hours if shift else 8.0
            if rec.check_out_time:
                rec.overtime_hours = max(0.0, round(rec.working_hours - full_day_hours, 2))
            else:
                rec.overtime_hours = 0.0

            half_day_hours = shift.half_day_hours if shift else 4.0
            if rec.check_out_time and rec.working_hours < half_day_hours:
                rec.status = 'half_day'
            elif rec.late_minutes > 0:
                rec.status = 'late'
            else:
                rec.status = 'present'

    def _haversine_km(self):
        self.ensure_one()
        if not (self.checkin_latitude and self.checkin_longitude
                and self.checkout_latitude and self.checkout_longitude):
            return 0.0
        from geopy.distance import geodesic
        try:
            return round(geodesic(
                (self.checkin_latitude, self.checkin_longitude),
                (self.checkout_latitude, self.checkout_longitude),
            ).km, 3)
        except Exception:
            return 0.0

    def _compute_late_minutes(self, shift):
        self.ensure_one()
        if not self.check_in_time or not shift:
            return 0.0
        check_in_local = fields.Datetime.context_timestamp(self, self.check_in_time)
        shift_start_hour = int(shift.start_time)
        shift_start_minute = int(round((shift.start_time - shift_start_hour) * 60))
        scheduled = check_in_local.replace(hour=shift_start_hour, minute=shift_start_minute, second=0, microsecond=0)
        grace = timedelta(minutes=shift.grace_minutes)
        if check_in_local > scheduled + grace:
            return round((check_in_local - scheduled).total_seconds() / 60.0, 1)
        return 0.0
