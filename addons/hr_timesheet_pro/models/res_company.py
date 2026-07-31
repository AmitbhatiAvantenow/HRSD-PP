from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    timesheet_pro_weekly_target_hours = fields.Float(
        string='Weekly Target Hours', default=40.0,
        help='Expected working hours per week, used as the target for the weekly effort progress bar.')
