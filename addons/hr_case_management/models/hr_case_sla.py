# -*- coding: utf-8 -*-
from odoo import fields, models


class HrCaseSla(models.Model):
    """SLA policy that determines how long support has to respond / resolve
    a case before it is considered breached and escalated, per
    Category + Priority combination."""
    _name = 'hr.case.sla'
    _description = 'HR Case SLA Policy'
    _order = 'priority, name'

    name = fields.Char(required=True)
    category_id = fields.Many2one('hr.case.category', string='Category',
                                   help='Leave empty to use this policy as the default '
                                        'fallback for the chosen priority.')
    priority = fields.Selection([
        ('1', '1 - Critical'),
        ('2', '2 - High'),
        ('3', '3 - Moderate'),
        ('4', '4 - Low'),
        ('5', '5 - Planning'),
    ], required=True, default='3')
    response_hours = fields.Float(string='Response Time (Hours)', default=4.0,
                                   help='Target time to acknowledge / start working the case.')
    resolution_hours = fields.Float(string='Resolution Time (Hours)', required=True, default=24.0,
                                     help='Target time to fully resolve the case.')
    escalation_hours = fields.Float(string='Escalate After (Hours)', required=True, default=48.0,
                                     help='If the case is still open after this many hours from '
                                          'opening, it is marked SLA Breached and escalated.')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _uniq_cat_priority_company = models.Constraint(
        'unique(category_id, priority, company_id)',
        'Only one SLA policy is allowed per Category / Priority / Company combination.',
    )
