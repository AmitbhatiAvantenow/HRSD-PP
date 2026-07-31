from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    flutterattendance_gps_radius = fields.Integer(
        string='GPS Check-in Radius (meters)',
        config_parameter='flutterattendance.gps_radius_meters',
        default=200,
        help="Maximum allowed distance from the office to check in. "
             "Leave office latitude/longitude empty to disable this check.",
    )
    flutterattendance_office_latitude = fields.Float(
        string='Office Latitude', digits=(10, 7),
        config_parameter='flutterattendance.office_latitude',
    )
    flutterattendance_office_longitude = fields.Float(
        string='Office Longitude', digits=(10, 7),
        config_parameter='flutterattendance.office_longitude',
    )
    flutterattendance_notifications_enabled = fields.Boolean(
        string='Enable Check-in/Check-out Reminders',
        config_parameter='flutterattendance.notifications_enabled',
        default=True,
    )
    flutterattendance_checkin_reminder_time = fields.Float(
        string='Check-in Reminder Time',
        config_parameter='flutterattendance.checkin_reminder_time',
        default=9.0, help="24h format, e.g. 9.0 = 09:00",
    )
    flutterattendance_checkout_reminder_time = fields.Float(
        string='Check-out Reminder Time',
        config_parameter='flutterattendance.checkout_reminder_time',
        default=18.0, help="24h format, e.g. 18.0 = 18:00",
    )
