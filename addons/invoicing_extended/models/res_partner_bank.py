# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    ifsc_code = fields.Char(
        string='IFSC Code',
        help="Indian Financial System Code of the bank branch, printed on "
             "invoices alongside the SWIFT code.")
