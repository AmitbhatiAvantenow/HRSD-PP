from odoo import api, fields, models


class FlutterNotificationAttendancePushCron(models.AbstractModel):
    _name = 'flutternotification.attendance.push.cron'
    _description = 'Backup FCM/APNs push for employees still checked in past the checkout reminder time'

    @api.model
    def _cron_push_checkout_backup(self):
        """Real push-notification counterpart to
        flutterattendance.notification._cron_send_reminders' checkout
        branch — same "open session past checkout hour" signal (Odoo has no
        continuous location channel, so it can never re-detect "walked
        outside the geofence" itself), but delivered via FCM/APNs instead of
        only the in-app pull notification. This is the safety net for when
        the app's on-device geofence-exit detection never fired — e.g. the
        employee force-stopped the app, which also kills the OS-level
        geofence receiver.
        """
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param('flutterattendance.notifications_enabled', 'True') not in ('True', '1', 'true'):
            return

        checkout_hour = float(icp.get_param('flutterattendance.checkout_reminder_time', '18.0') or 18.0)

        Employee = self.env['hr.employee'].sudo()
        Attendance = self.env['flutterattendance.attendance'].sudo()
        PushLog = self.env['flutternotification.push_log'].sudo()
        PushService = self.env['flutternotification.push.service']

        employees = Employee.search([('mobile_app_access', '=', True), ('user_id', '!=', False)])
        for employee in employees:
            now_local = fields.Datetime.context_timestamp(employee, fields.Datetime.now())
            today = now_local.date()
            current_hour = now_local.hour + now_local.minute / 60.0
            if current_hour < checkout_hour:
                continue

            todays_attendance = Attendance.search([
                ('employee_id', '=', employee.id),
                ('attendance_date', '=', today),
            ], order='check_in_time desc', limit=1)
            if not todays_attendance or todays_attendance.check_out_time:
                continue

            # One attempt per attendance session per day — the cron runs
            # every 15 minutes, so without this it would re-push the same
            # reminder all evening.
            if PushLog.search_count([
                ('attendance_id', '=', todays_attendance.id),
                ('kind', '=', 'backup_checkout_reminder'),
            ]):
                continue

            PushService.send_to_employee(
                employee,
                title='Forgot to check out?',
                body="You're still checked in — tap to check out now.",
                data={'action': 'CHECKOUT_ACTION'},
                kind='backup_checkout_reminder',
                attendance=todays_attendance,
            )
