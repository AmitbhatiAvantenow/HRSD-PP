from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    flutternotification_firebase_project_id = fields.Char(
        string='Firebase Project ID',
        config_parameter='flutternotification.firebase_project_id',
        help="Used for Android push (FCM HTTP v1). A free Firebase console project is "
             "needed only so the Android app can obtain an FCM token — Odoo sends "
             "pushes directly via FCM's REST API, not the Firebase Admin SDK.",
    )
    # res.config.settings only allows boolean/integer/float/char/selection/
    # many2one/datetime fields (see odoo/addons/base/models/res_config.py
    # _get_classified_fields) — Text isn't supported there, even though
    # Char is unbounded in Postgres just like Text, so nothing is lost.
    flutternotification_firebase_service_account_json = fields.Char(
        string='Firebase Service Account JSON',
        config_parameter='flutternotification.firebase_service_account_json',
        help="Paste the full JSON key downloaded from Firebase Console > Project "
             "Settings > Service Accounts (role: Firebase Cloud Messaging API Admin).",
    )
    flutternotification_apns_key_id = fields.Char(
        string='APNs Key ID',
        config_parameter='flutternotification.apns_key_id',
    )
    flutternotification_apns_team_id = fields.Char(
        string='Apple Team ID',
        config_parameter='flutternotification.apns_team_id',
    )
    flutternotification_apns_bundle_id = fields.Char(
        string='iOS Bundle ID',
        config_parameter='flutternotification.apns_bundle_id',
    )
    flutternotification_apns_p8_key = fields.Char(
        string='APNs Auth Key (.p8)',
        config_parameter='flutternotification.apns_p8_key',
        help="Paste the contents of the .p8 key file downloaded from Apple Developer > "
             "Certificates, Identifiers & Profiles > Keys.",
    )
    flutternotification_apns_use_sandbox = fields.Boolean(
        string='Use APNs Sandbox',
        config_parameter='flutternotification.apns_use_sandbox',
        help="Enable while testing with a development-signed build; disable for "
             "TestFlight/App Store builds.",
    )

    def action_send_test_push(self):
        """Push Settings > Send Test Push button — sends a test notification to
        the current user's own employee record/device, so an admin can verify
        Firebase/APNs credentials are wired up correctly without waiting for
        the next cron run or asking an employee to test it."""
        self.ensure_one()
        employee = self.env.user.employee_id
        if not employee:
            return
        self.env['flutternotification.push.service'].send_to_employee(
            employee,
            title='Test notification',
            body='Push notifications are configured correctly.',
            kind='test',
        )
