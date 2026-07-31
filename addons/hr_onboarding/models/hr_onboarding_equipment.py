from odoo import fields, models


class HrOnboardingEquipment(models.Model):
    _name = 'hr.onboarding.equipment'
    _description = 'Onboarding Equipment'
    _order = 'id desc'

    name = fields.Char(required=True)
    onboarding_id = fields.Many2one('hr.onboarding', required=True, ondelete='cascade', index=True)
    equipment_type = fields.Selection([
        ('laptop', 'Laptop'),
        ('monitor', 'Monitor'),
        ('mouse', 'Mouse'),
        ('keyboard', 'Keyboard'),
        ('headset', 'Headset'),
        ('id_card', 'ID Card'),
        ('access_card', 'Access Card'),
        ('sim', 'SIM Card'),
        ('phone', 'Phone'),
        ('locker', 'Locker'),
        ('other', 'Other'),
    ], required=True, default='other')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
    ], default='pending', required=True)
    serial_number = fields.Char()
    assigned_date = fields.Date()
