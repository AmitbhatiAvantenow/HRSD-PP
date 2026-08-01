from odoo import fields, models


class FlutterAttendanceDevice(models.Model):
    _name = 'flutterattendance.device'
    _description = 'Mobile Device'
    _rec_name = 'device_name'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    device_id = fields.Char(required=True, index=True, help="Unique device identifier reported by the app")
    device_name = fields.Char()
    os_version = fields.Char(string='OS Version')
    app_version = fields.Char()
    fcm_token = fields.Char(
        string='FCM Token',
        help="Reserved for future push-notification wiring; not currently used to send anything.",
    )
    last_login = fields.Datetime()
    last_sync = fields.Datetime()
    active = fields.Boolean(default=True)

    # One-device-per-employee binding. A brand new employee's first login
    # auto-activates; logging in from any other device while one is
    # already 'active' is rejected at /api/login and lands here as
    # 'pending' until an admin approves it (see action_approve).
    state = fields.Selection(
        [('active', 'Active'), ('pending', 'Pending Approval'), ('revoked', 'Revoked')],
        default='pending', required=True, index=True,
    )
    # jti of the most recently issued token for this device, so approving
    # a replacement device can revoke the previous device's live session
    # instead of waiting for its 24h token to expire on its own.
    current_jti = fields.Char()

    _device_employee_uniq = models.Constraint(
        'unique(employee_id, device_id)',
        'This device is already registered for this employee.',
    )

    def action_approve(self):
        """Make this device the employee's one active device, demoting
        (and logging out) whichever device held that spot before."""
        for device in self:
            others = self.search([
                ('employee_id', '=', device.employee_id.id),
                ('state', '=', 'active'),
                ('id', '!=', device.id),
            ])
            if others:
                RevokedToken = self.env['flutterlogin.revoked.token'].sudo()
                for other in others:
                    if other.current_jti:
                        RevokedToken.create({'jti': other.current_jti, 'user_id': device.employee_id.user_id.id})
                others.write({'state': 'revoked', 'current_jti': False})
            device.state = 'active'

    def action_reject(self):
        self.write({'state': 'revoked', 'current_jti': False})
