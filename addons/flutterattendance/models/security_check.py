from odoo import fields, models


class FlutterAttendanceSecurityCheck(models.Model):
    _name = 'flutterattendance.security.check'
    _description = 'Mobile Attendance Security Check'
    _order = 'sequence, id'

    check_type = fields.Selection(
        [
            ('mock_location', 'Location Spoofing (Mock GPS)'),
            ('vpn', 'VPN / Proxy Detection'),
            ('root_jailbreak', 'Root / Jailbreak Detection'),
            ('dev_mode', 'Developer Mode Detection'),
            ('real_device', 'Emulator Detection'),
            ('impossible_travel', 'Impossible Travel Detection'),
            ('face_recognition', 'Face Recognition'),
        ],
        required=True, index=True,
    )
    name = fields.Char(required=True, help="Shown to admins on the Settings screen.")
    description = fields.Char(help="Short explanation of what this check does.")
    icon = fields.Char(help="Icon identifier for the settings card, e.g. a fa- class name.")
    sequence = fields.Integer(default=10)
    enabled = fields.Boolean(default=True, help="Whether this check runs at all.")

    # Employees this check skips entirely, even while `enabled` is True.
    # Everyone not in this list is guarded by the check normally — this is
    # an exemption list (e.g. an admin exempting their own account while
    # testing), not a scope restriction.
    exempt_employee_ids = fields.Many2many(
        'hr.employee', 'flutterattendance_security_check_exempt_employee_rel',
        'check_id', 'employee_id',
        string='Exempted Employees',
        help="These employees are NOT subject to this check, even when it's enabled. "
             "Everyone else is checked normally.",
    )

    _check_type_uniq = models.Constraint(
        'unique(check_type)',
        'A security check of this type already exists.',
    )

    def get_effective_settings(self, employee):
        """{check_type: bool} for every configured check, folding in the
        per-check exemption list — False only where the check is disabled
        outright, or this specific employee is exempted from it."""
        return {
            check.check_type: check.enabled and employee not in check.exempt_employee_ids
            for check in self.search([])
        }
