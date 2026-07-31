from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    mobile_app_access = fields.Boolean(
        string='Mobile App Access',
        default=True,
        help="Allow this employee to log in through the Flutter mobile app.",
    )
