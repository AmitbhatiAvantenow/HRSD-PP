# -*- coding: utf-8 -*-
from odoo import fields, models


class HrsdDashboardNavbarItem(models.Model):
    _name = 'hrsd.dashboard.navbar.item'
    _description = 'HR Portal Top Navigation Item'
    _order = 'sequence, id'

    name = fields.Char(string='Label', required=True)
    url = fields.Char(string='Link', required=True, default='#',
                       help='Where this link opens, e.g. /odoo/employees or /hrsd/appraisal')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    group_ids = fields.Many2many(
        'res.groups', 'hrsd_dashboard_navbar_item_group_rel', 'navbar_item_id', 'group_id',
        string='Visible to Groups',
        help='Restrict this link to users in one (or more) of these groups. '
             'Leave empty to show it to everyone. Administrators always see everything.')
