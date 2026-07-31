# -*- coding: utf-8 -*-
from odoo import fields, models

# The 5 built-in dashboard stats. Values are always computed live in
# hrsd_dashboard.py; this model only controls which of them show up for
# which users, and in what order — not the numbers themselves.
STAT_CARD_KEYS = [
    ('total_employees', 'Total Employees'),
    ('on_leave_today', 'On Leave Today'),
    ('pending_requests', 'Pending Requests'),
    ('payroll_this_month', 'Payroll This Month'),
    ('attendance_rate', 'Attendance Rate'),
]


class HrsdDashboardStatCard(models.Model):
    _name = 'hrsd.dashboard.stat.card'
    _description = 'HR Portal Dashboard Stat Card'
    _order = 'sequence, id'

    key = fields.Selection(STAT_CARD_KEYS, string='Stat', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    group_ids = fields.Many2many(
        'res.groups', 'hrsd_dashboard_stat_card_group_rel', 'stat_card_id', 'group_id',
        string='Visible to Groups',
        help='Restrict this stat card to users in one (or more) of these groups. '
             'Leave empty to show it to everyone. Administrators always see everything.')
