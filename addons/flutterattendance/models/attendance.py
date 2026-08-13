import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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
    status = fields.Selection(
        selection='_get_status_selection', compute='_compute_summary', store=True,
        help="Driven by Mobile Attendance > Settings > Status Rules — fully configurable, "
             "including adding brand new statuses beyond Present/Late/Half Day.",
    )
    remarks = fields.Text(string='Work Comment', help="Employee's work summary, collected right after check-out.")
    missed_checkout = fields.Boolean(
        default=False,
        help="True when this session's employee-local day ended (or a later check-in happened) "
             "before a check-out was ever recorded — the checkout was missed, so the session was "
             "auto-closed instead of blocking the next check-in. Cleared automatically if HR later "
             "fills in a real check-out time.",
    )

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

    @api.model
    def _resolve_stale_session(self, employee, today):
        """Look up this employee's open session (if any) and decide whether
        it should still block a new check-in.

        A session left open from a previous day means the check-out was
        simply forgotten, not that the employee is still "at work" — so
        instead of blocking today's check-in forever, it's auto-closed here
        as missed_checkout and this returns None, letting the caller create
        today's record. A session still open for *today* is a real
        in-progress check-in and is returned as-is so the caller can reject
        the duplicate check-in.
        """
        open_session = self._find_open_session(employee)
        if not open_session:
            return None
        if open_session.attendance_date and open_session.attendance_date < today:
            open_session.write({'missed_checkout': True})
            return None
        return open_session

    @api.model
    def _cron_flag_missed_checkouts(self):
        """Safety net for _resolve_stale_session: catches sessions left open
        from a previous day even when the employee never opens the app again
        to trigger a new check-in (so HR/reports still see them flagged
        instead of looking like an endless open session)."""
        open_sessions = self.sudo().search([
            ('check_out_time', '=', False),
            ('missed_checkout', '=', False),
        ])
        stale = self.browse()
        for rec in open_sessions:
            employee = rec.employee_id
            tz_name = employee.tz or employee.user_id.tz or 'UTC'
            today_local = fields.Datetime.context_timestamp(
                rec.with_context(tz=tz_name), fields.Datetime.now()).date()
            if rec.attendance_date and rec.attendance_date < today_local:
                stale += rec
        if stale:
            stale.write({'missed_checkout': True})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # A plain check-in has no check_out_time yet, so there is nothing
        # complete to roll into the timesheet; only a (rare) creation that
        # already carries a check-out needs an immediate sync.
        records.filtered('check_out_time')._sync_to_timesheet()
        return records

    def write(self, vals):
        # A real check-out time arriving (the normal check-out call, or HR
        # backfilling one via history_update) means the checkout was no
        # longer missed, even if this session had earlier been auto-flagged
        # by _resolve_stale_session/_cron_flag_missed_checkouts.
        if vals.get('check_out_time') and 'missed_checkout' not in vals:
            vals = {**vals, 'missed_checkout': False}
        sync_keys = {'check_in_time', 'check_out_time', 'attendance_date', 'remarks', 'employee_id'}
        to_sync = self if sync_keys & set(vals) else self.browse()
        # attendance_date/employee_id can move a record's hours out of its old
        # day/employee bucket, so that bucket needs to be recomputed too, not
        # just the one the record lands in after the write. Unlike the
        # current-bucket sync below, this one is allowed to clear a day's
        # line down to zero since the record genuinely left that bucket.
        stale = self.filtered(lambda r: r.employee_id and r.attendance_date) if ('attendance_date' in vals or 'employee_id' in vals) else self.browse()
        stale_keys = [(r.employee_id.id, r.attendance_date) for r in stale]
        res = super().write(vals)
        for employee_id, attendance_date in stale_keys:
            self.browse()._sync_day_to_timesheet(self.env['hr.employee'].browse(employee_id), attendance_date, allow_clear=True)
        to_sync._sync_to_timesheet()
        return res

    def unlink(self):
        day_keys = {(r.employee_id.id, r.attendance_date) for r in self}
        res = super().unlink()
        for employee_id, attendance_date in day_keys:
            self.browse()._sync_day_to_timesheet(self.env['hr.employee'].browse(employee_id), attendance_date, allow_clear=True)
        return res

    def _sync_to_timesheet(self):
        for employee_id, attendance_date in {(r.employee_id.id, r.attendance_date) for r in self}:
            self._sync_day_to_timesheet(self.env['hr.employee'].browse(employee_id), attendance_date)

    def _sync_day_to_timesheet(self, employee, attendance_date, allow_clear=False):
        """Roll every completed flutterattendance session for `employee` on
        `attendance_date` into the matching day-line of that employee's
        weekly hr.timesheet.sheet, creating the week/day if needed.

        `allow_clear` controls what happens when there is no longer any
        completed session for that day: callers that just removed or moved a
        record (unlink, or a write changing attendance_date/employee_id) pass
        True so the day-line is zeroed back out; a routine check-in or
        in-place edit passes False so an open (not-yet-checked-out) session,
        or an unrelated field edit, can never wipe hours someone already
        filled in for that day.

        Best-effort: never lets a timesheet issue (locked week, missing
        sequence, etc.) break the mobile check-in/check-out API call that
        triggered it.
        """
        if not (employee and attendance_date):
            return
        try:
            self.sudo()._do_sync_day_to_timesheet(employee.sudo(), attendance_date, allow_clear)
        except Exception:
            _logger.warning(
                "flutterattendance: failed to sync attendance for employee %s on %s to timesheet",
                employee.id, attendance_date, exc_info=True,
            )

    def _do_sync_day_to_timesheet(self, employee, attendance_date, allow_clear):
        Sheet = self.env['hr.timesheet.sheet']
        Line = self.env['hr.timesheet.line']

        day_records = self.search([
            ('employee_id', '=', employee.id),
            ('attendance_date', '=', attendance_date),
            ('check_out_time', '!=', False),
        ])

        week_start = attendance_date - timedelta(days=attendance_date.weekday())
        sheet = Sheet.search([
            ('employee_id', '=', employee.id),
            ('date_start', '=', week_start),
        ], limit=1)

        if not day_records:
            if allow_clear and sheet and sheet.state in ('draft', 'returned'):
                line = sheet.line_ids.filtered(lambda l: l.date == attendance_date)
                line.write({'start_time': 0.0, 'end_time': 0.0, 'hours': 0.0})
            return

        if not sheet:
            # Deliberately not Sheet._build_week_lines(): that helper is the
            # "New timesheet" convenience template (09:00-17:00 / 8h on every
            # weekday) for a human to then fill in by hand. A week created
            # from mobile attendance must start blank so any day without a
            # check-in/out stays empty instead of looking like a full day
            # was worked.
            sheet = Sheet.create({
                'employee_id': employee.id,
                'company_id': employee.company_id.id,
                'date_start': week_start,
                'line_ids': [(0, 0, {
                    'date': week_start + timedelta(days=i),
                    'start_time': 0.0,
                    'end_time': 0.0,
                    'hours': 0.0,
                    'billable': False,
                }) for i in range(7)],
            })

        if sheet.state not in ('draft', 'returned'):
            _logger.info(
                "flutterattendance: timesheet %s is locked (state=%s); skipping auto-sync for %s",
                sheet.name, sheet.state, attendance_date,
            )
            return

        total_hours = sum(day_records.mapped('working_hours'))
        first_in = min(day_records.mapped('check_in_time'))
        last_out = max(day_records.mapped('check_out_time'))
        remarks = ' | '.join(r.remarks.strip() for r in day_records if r.remarks and r.remarks.strip())

        # Convert using the employee's own timezone, not whichever user/
        # context happens to be running the sync (mobile check-in, an HR
        # edit, a cron, a shell backfill...) - otherwise the same attendance
        # can convert to a different clock time depending on who triggered it.
        tz_self = self.with_context(tz=employee.tz or employee.user_id.tz or 'UTC')
        check_in_local = fields.Datetime.context_timestamp(tz_self, first_in)
        check_out_local = fields.Datetime.context_timestamp(tz_self, last_out)

        line_vals = {
            'start_time': check_in_local.hour + check_in_local.minute / 60.0,
            'end_time': check_out_local.hour + check_out_local.minute / 60.0,
            'hours': round(total_hours, 2),
            'billable': True,
        }
        if remarks:
            line_vals['comments'] = remarks

        line = sheet.line_ids.filtered(lambda l: l.date == attendance_date)
        if line:
            line.write(line_vals)
        else:
            Line.create({**line_vals, 'sheet_id': sheet.id, 'date': attendance_date})

    def _get_status_selection(self):
        rules = self.env['flutterattendance.status.rule'].with_context(active_test=False).sudo().search(
            [], order='sequence, id')
        selection = list(dict.fromkeys((rule.code, rule.name) for rule in rules))
        default_code = self.env['ir.config_parameter'].sudo().get_param(
            'flutterattendance.status_default_code', 'present')
        if default_code not in dict(selection):
            selection.append((default_code, default_code.replace('_', ' ').title()))
        if not selection:
            selection = [('present', 'Present'), ('late', 'Late'), ('half_day', 'Half Day')]
        return selection

    @api.depends('check_in_time', 'check_out_time', 'missed_checkout',
                 'checkin_latitude', 'checkin_longitude', 'checkout_latitude', 'checkout_longitude')
    def _compute_summary(self):
        ICP = self.env['ir.config_parameter'].sudo()
        # ir.config_parameter.set_param() deletes the row entirely for a
        # False boolean rather than storing the string 'False' - so a missing
        # key must read as disabled, not as "default enabled", or an admin's
        # explicit uncheck would be indistinguishable from never-configured.
        auto_enabled = ICP.get_param('flutterattendance.status_auto_enabled') == 'True'
        default_code = ICP.get_param('flutterattendance.status_default_code', 'present')
        rules = self.env['flutterattendance.status.rule'].sudo().search([], order='sequence, id') \
            if auto_enabled else self.env['flutterattendance.status.rule']

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

            rec.status = rec._match_status_rule(rules, shift) if auto_enabled else default_code

    def _match_status_rule(self, rules, shift):
        """First rule (in sequence order) whose condition matches this record's
        worked hours / lateness wins; falls back to the configured default code
        if none match, so a bad rule set never leaves Status empty."""
        self.ensure_one()
        for rule in rules:
            if rule.require_checkout and not self.check_out_time:
                continue

            if rule.condition == 'missed_checkout':
                if self.missed_checkout:
                    return rule.code
            elif rule.condition == 'shift_half_day':
                half_day_hours = shift.half_day_hours if shift else 4.0
                if self.check_out_time and self.working_hours < half_day_hours:
                    return rule.code
            elif rule.condition == 'hours_range':
                if self.working_hours >= rule.min_hours and (rule.max_hours <= 0 or self.working_hours < rule.max_hours):
                    return rule.code
            elif rule.condition == 'late':
                if self.late_minutes > 0:
                    return rule.code
            elif rule.condition == 'always':
                return rule.code

        return self.env['ir.config_parameter'].sudo().get_param('flutterattendance.status_default_code', 'present')

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
