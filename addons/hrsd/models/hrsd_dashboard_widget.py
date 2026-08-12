# -*- coding: utf-8 -*-
from odoo import fields, models

# The 2 built-in dashboard widgets (Recent Activities, Upcoming Birthdays).
# Unlike stat cards / top-nav links / dashboard menus (which default to
# "visible to everyone"), these default to Administrators-only — add
# groups below to open a widget up to more users.
DASHBOARD_WIDGET_KEYS = [
    ('recent_activities', 'Recent Activities'),
    ('upcoming_birthdays', 'Upcoming Birthdays'),
]


class HrsdDashboardWidget(models.Model):
    _name = 'hrsd.dashboard.widget'
    _description = 'HR Portal Dashboard Widget'
    _order = 'id'

    key = fields.Selection(DASHBOARD_WIDGET_KEYS, string='Widget', required=True)
    active = fields.Boolean(string='Active', default=True)
    group_ids = fields.Many2many(
        'res.groups', 'hrsd_dashboard_widget_group_rel', 'widget_id', 'group_id',
        string='Visible to Groups',
        help='This widget is only visible to Administrators by default. '
             'Add one or more groups here to let their members see it too.')
