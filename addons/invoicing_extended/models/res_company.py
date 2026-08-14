# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_tagline = fields.Char(
        string='Invoice Tagline',
        help="Short tagline printed under the logo on the extended invoice, "
             "e.g. 'Quant Analytics with Agility'.")
    invoice_default_ccw_percent = fields.Float(
        string='Default CCW Deduction (%)',
        help="Default deduction percentage (e.g. Consultant Contribution/Welfare) "
             "applied on staff-augmentation invoices, editable per invoice.")
    invoice_default_lut_arn = fields.Char(
        string='Default LUT ARN',
        help="Default ARN for the LUT (Letter of Undertaking) application quoted "
             "on export invoices raised without payment of IGST.")
    invoice_signatory_name = fields.Char(string='Authorized Signatory Name')
    invoice_signatory_designation = fields.Char(string='Authorized Signatory Designation')
    invoice_signatory_signature = fields.Binary(string='Authorized Signatory Signature')
