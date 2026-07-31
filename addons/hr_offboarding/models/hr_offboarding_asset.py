from odoo import fields, models


class HrOffboardingAsset(models.Model):
    _name = 'hr.offboarding.asset'
    _description = 'Offboarding Asset Return'
    _order = 'id desc'

    name = fields.Char(required=True)
    request_id = fields.Many2one('hr.offboarding.request', required=True, ondelete='cascade', index=True)
    asset_type = fields.Selection([
        ('laptop', 'Laptop'),
        ('monitor', 'Monitor'),
        ('keyboard', 'Keyboard'),
        ('mouse', 'Mouse'),
        ('phone', 'Phone'),
        ('sim', 'SIM Card'),
        ('id_card', 'ID Card'),
        ('access_card', 'Access Card'),
        ('headset', 'Headset'),
        ('usb_key', 'USB Key'),
        ('locker_key', 'Locker Key'),
        ('parking_card', 'Parking Card'),
        ('other', 'Other'),
    ], required=True, default='other')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('returned', 'Returned'),
        ('damaged', 'Damaged'),
        ('lost', 'Lost'),
    ], default='pending', required=True)
    serial_number = fields.Char()
    condition = fields.Selection([
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('damaged', 'Damaged'),
    ])
    assigned_date = fields.Date()
    return_date = fields.Date()
    damage_notes = fields.Text()
    replacement_cost = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
