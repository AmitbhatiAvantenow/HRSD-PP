from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

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

    # Cosine-similarity threshold for the face_engine embedder — 0.45 is a
    # starting point empirically validated against buffalo_sc's MobileFaceNet
    # (same-person similarity ~0.9 even across lighting/compression changes,
    # different-person ~0.0-0.05), not the illustrative "> 0.75" some naive
    # specs suggest — tune from real check-in data once this is live.
    flutterattendance_face_similarity_threshold = fields.Float(
        string='Face Match Threshold',
        config_parameter='flutterattendance.face_similarity_threshold',
        default=0.45, help="Cosine similarity (0-1) above which a selfie is considered a match.",
    )
    flutterattendance_face_max_attempts = fields.Integer(
        string='Max Face Verification Attempts',
        config_parameter='flutterattendance.face_max_attempts',
        default=5, help="After this many failed match attempts, check-in/out escalates to HR approval.",
    )

    flutterattendance_status_auto_enabled = fields.Boolean(
        string='Automatically Calculate Attendance Status',
        config_parameter='flutterattendance.status_auto_enabled',
        default=True,
        help="When off, every attendance record is simply set to the Default Status below "
             "(e.g. always 'Present'), ignoring the Status Rules entirely.",
    )
    flutterattendance_status_default_code = fields.Char(
        string='Default Status',
        config_parameter='flutterattendance.status_default_code',
        default='present',
        help="Used when auto-calculation is off above, and as the fallback if a record matches "
             "none of the active Status Rules. Must match a Status Rule's Code, e.g. 'present'.",
    )

    def action_recompute_attendance_status(self):
        """Re-run status calculation on every existing Mobile Attendance record
        using the Status Rules / toggle as they stand right now. Not automatic:
        new check-ins/check-outs always pick up the latest rules on their own
        (Status is computed at save time), so this is only needed if an admin
        also wants past records to reflect a rule change they just made."""
        self.ensure_one()
        records = self.env['flutterattendance.attendance'].sudo().search([])
        records._compute_summary()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Attendance Status Updated'),
                'message': _('%s record(s) recalculated using the current Status Rules.') % len(records),
                'type': 'success',
                'sticky': False,
            },
        }
