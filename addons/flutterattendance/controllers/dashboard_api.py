from odoo import fields, http
from odoo.http import request

from odoo.addons.flutterlogin.controllers.auth_controller import token_required, _json_response


class FlutterAttendanceDashboardController(http.Controller):

    @http.route('/api/dashboard', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def dashboard(self, employee=None, **kwargs):
        Attendance = request.env['flutterattendance.attendance'].sudo()
        today = fields.Date.context_today(employee)

        today_records = Attendance.search([
            ('employee_id', '=', employee.id),
            ('attendance_date', '=', today),
        ], order='check_in_time asc')
        open_session = today_records.filtered(lambda r: not r.check_out_time)
        last = today_records[-1] if today_records else None
        last_check_out = next((r.check_out_time for r in reversed(today_records) if r.check_out_time), False)

        closed_hours = sum(r.working_hours for r in today_records if r.check_out_time)
        if open_session:
            open_seconds = (fields.Datetime.now() - open_session[0].check_in_time).total_seconds()
            working_hours_today = closed_hours + open_seconds / 3600.0
        else:
            working_hours_today = closed_hours

        shift = employee.attendance_shift_id

        month_start = today.replace(day=1)
        month_records = Attendance.search([
            ('employee_id', '=', employee.id),
            ('attendance_date', '>=', month_start),
            ('attendance_date', '<=', today),
        ])
        days_present = len(set(month_records.mapped('attendance_date')))
        # Shift-aware: only the days this employee's shift actually treats
        # as working days count toward the denominator — a shift with a
        # Tue-Sun week, or Saturdays on, isn't punished for "missing"
        # Mondays it was never scheduled to work.
        if shift:
            total_working_days = shift.working_days_between(month_start, today)
        else:
            total_working_days = (today - month_start).days + 1
        attendance_percentage = (
            round((days_present / total_working_days) * 100, 1) if total_working_days else 0.0
        )
        total_hours = sum(month_records.mapped('working_hours'))
        avg_work_per_day = round(total_hours / days_present, 2) if days_present else 0.0

        return _json_response({
            'success': True,
            'is_checked_in': bool(open_session),
            # today_records is ordered oldest-first, so the most recent
            # check-in (what "Last Check In" on Home should show) is the
            # last element, not the first — a day with more than one
            # check-in/out cycle was otherwise stuck showing the first one.
            'last_check_in': today_records[-1].check_in_time.isoformat() if today_records else False,
            'last_check_out': last_check_out.isoformat() if last_check_out else False,
            'working_hours_today': round(working_hours_today, 2),
            'late_by_minutes': last.late_minutes if last else 0.0,
            'overtime_hours': last.overtime_hours if last else 0.0,
            'today_status': last.status if last else 'not_checked_in',
            'shift': {
                'name': shift.name if shift else False,
                'start_time': shift.start_time if shift else False,
                'end_time': shift.end_time if shift else False,
                'break_start_time': shift.break_start_time if shift else False,
                'break_minutes': shift.break_minutes if shift else False,
                'grace_minutes': shift.grace_minutes if shift else False,
                'half_day_hours': shift.half_day_hours if shift else False,
                'full_day_hours': shift.full_day_hours if shift else False,
                'working_days': {
                    'monday': shift.monday, 'tuesday': shift.tuesday, 'wednesday': shift.wednesday,
                    'thursday': shift.thursday, 'friday': shift.friday, 'saturday': shift.saturday,
                    'sunday': shift.sunday,
                } if shift else False,
            },
            'month': {
                'days_present': days_present,
                'total_working_days': total_working_days,
                'attendance_percentage': attendance_percentage,
                'avg_work_per_day': avg_work_per_day,
            },
        })
