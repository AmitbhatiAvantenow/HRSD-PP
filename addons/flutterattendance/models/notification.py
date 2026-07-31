from odoo import api, fields, models


class FlutterAttendanceNotification(models.Model):
    _name = 'flutterattendance.notification'
    _description = 'In-app Notification (fetched by the Flutter app; no push service involved)'
    _order = 'create_date desc'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    notif_type = fields.Selection([
        ('checkin_reminder', 'Check-in Reminder'),
        ('checkout_reminder', 'Check-out Reminder'),
        ('custom', 'Custom'),
    ], required=True, default='custom')
    title = fields.Char(required=True)
    body = fields.Char()
    for_date = fields.Date(
        default=fields.Date.context_today,
        help="Business date this notification relates to (used to avoid sending duplicate daily reminders).",
    )
    is_read = fields.Boolean(default=False)
    read_at = fields.Datetime()

    @api.model
    def _cron_send_reminders(self):
        """Create pending check-in/check-out reminder notifications.

        Pull-based: the Flutter app must poll GET /api/notifications to see
        these (there is no Firebase/APNs push involved by design).
        """
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param('flutterattendance.notifications_enabled', 'True') not in ('True', '1', 'true'):
            return

        checkin_hour = float(icp.get_param('flutterattendance.checkin_reminder_time', '9.0') or 9.0)
        checkout_hour = float(icp.get_param('flutterattendance.checkout_reminder_time', '18.0') or 18.0)

        Employee = self.env['hr.employee'].sudo()
        Attendance = self.env['flutterattendance.attendance'].sudo()
        Notification = self.sudo()

        employees = Employee.search([('mobile_app_access', '=', True), ('user_id', '!=', False)])
        for employee in employees:
            now_local = fields.Datetime.context_timestamp(employee, fields.Datetime.now())
            today = now_local.date()
            current_hour = now_local.hour + now_local.minute / 60.0

            todays_attendance = Attendance.search([
                ('employee_id', '=', employee.id),
                ('attendance_date', '=', today),
            ], order='check_in_time desc', limit=1)

            if current_hour >= checkin_hour and not todays_attendance:
                if not Notification.search_count([
                    ('employee_id', '=', employee.id),
                    ('notif_type', '=', 'checkin_reminder'),
                    ('for_date', '=', today),
                ]):
                    Notification.create({
                        'employee_id': employee.id,
                        'notif_type': 'checkin_reminder',
                        'title': 'Check-in reminder',
                        'body': "Don't forget to check in for today.",
                        'for_date': today,
                    })

            if current_hour >= checkout_hour and todays_attendance and not todays_attendance.check_out_time:
                if not Notification.search_count([
                    ('employee_id', '=', employee.id),
                    ('notif_type', '=', 'checkout_reminder'),
                    ('for_date', '=', today),
                ]):
                    Notification.create({
                        'employee_id': employee.id,
                        'notif_type': 'checkout_reminder',
                        'title': 'Check-out reminder',
                        'body': "You're still checked in — remember to check out.",
                        'for_date': today,
                    })
