# -*- coding: utf-8 -*-
from odoo import api, fields, models

ICON_SELECTION = [
    ('users', 'Users'),
    ('user', 'User'),
    ('userPlus', 'User Plus'),
    ('userMinus', 'User Minus'),
    ('shieldCheck', 'Shield Check'),
    ('shield', 'Shield'),
    ('briefcase', 'Briefcase'),
    ('logOut', 'Log Out'),
    ('target', 'Target'),
    ('trendingUp', 'Trending Up'),
    ('award', 'Award'),
    ('calendarCheck', 'Calendar Check'),
    ('headset', 'Headset'),
    ('fileText', 'File Text'),
    ('gift', 'Gift'),
    ('arrowRight', 'Arrow Right'),
    ('bot', 'Bot'),
    ('scan', 'Scan'),
    ('messageCircle', 'Message Circle'),
    ('chartBar', 'Chart Bar'),
    ('clock', 'Clock'),
]

COLOR_SELECTION = [
    ('blue', 'Blue'),
    ('green', 'Green'),
    ('purple', 'Purple'),
    ('orange', 'Orange'),
    ('pink', 'Pink'),
    ('red', 'Red'),
    ('indigo', 'Indigo'),
]


class HrsdDashboardMenu(models.Model):
    _name = 'hrsd.dashboard.menu'
    _description = 'HR Portal Dashboard Menu'
    _order = 'sequence, id'

    name = fields.Char(string='Menu Title', required=True)
    description = fields.Text(string='Description')
    icon = fields.Selection(ICON_SELECTION, string='Icon', required=True, default='users')
    color = fields.Selection(COLOR_SELECTION, string='Color', required=True, default='blue')
    url = fields.Char(
        string='Direct Link',
        help='Optional. If set, clicking this tile navigates straight to this URL '
             'instead of opening its Submenu Items — use this for a menu that has no '
             'submenu cards of its own. Leave blank to keep the Submenu Items behavior.')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    group_ids = fields.Many2many(
        'res.groups', 'hrsd_dashboard_menu_group_rel', 'menu_id', 'group_id',
        string='Visible to Groups',
        help='Restrict this tile to users in one (or more) of these groups. '
             'Leave empty to show it to everyone. Administrators always see everything.')
    submenu_ids = fields.One2many(
        'hrsd.dashboard.submenu', 'menu_id', string='Submenu Items')
    submenu_count = fields.Integer(compute='_compute_submenu_count', string='Submenu Count')

    @api.depends('submenu_ids')
    def _compute_submenu_count(self):
        for rec in self:
            rec.submenu_count = len(rec.submenu_ids)


class HrsdDashboardSubmenu(models.Model):
    _name = 'hrsd.dashboard.submenu'
    _description = 'HR Portal Dashboard Submenu Item'
    _order = 'sequence, id'

    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    icon = fields.Selection(ICON_SELECTION, string='Icon', required=True, default='briefcase')
    color = fields.Selection(COLOR_SELECTION, string='Color', required=True, default='blue')
    url = fields.Char(string='Link', required=True, default='#',
                       help='Where this card opens when clicked, e.g. /odoo/employees or /hrsd/appraisal')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    group_ids = fields.Many2many(
        'res.groups', 'hrsd_dashboard_submenu_group_rel', 'submenu_id', 'group_id',
        string='Visible to Groups',
        help='Restrict this card to users in one (or more) of these groups. '
             'Leave empty to show it to everyone. Administrators always see everything.')
    menu_id = fields.Many2one(
        'hrsd.dashboard.menu', string='Menu', required=True, ondelete='cascade')
