from odoo import fields, models


class FlutterLoginRevokedToken(models.Model):
    _name = 'flutterlogin.revoked.token'
    _description = 'Revoked JWT (logout / refresh rotation)'
    _rec_name = 'jti'

    jti = fields.Char(string='Token ID', required=True, index=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    revoked_at = fields.Datetime(string='Revoked At', default=fields.Datetime.now, required=True)
