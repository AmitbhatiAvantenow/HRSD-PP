# -*- coding: utf-8 -*-
from urllib.parse import quote

from markupsafe import Markup

from odoo import api, fields, models


class EinvoiceResultWizard(models.TransientModel):
    _name = 'einvoice.result.wizard'
    _description = 'e-Invoice Result'

    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    title = fields.Char(readonly=True)
    irn = fields.Char(string='IRN', readonly=True)
    ack_no = fields.Char(string='Ack No', readonly=True)
    ack_date = fields.Datetime(string='Ack Date', readonly=True)
    signed_qr_code = fields.Text(string='Signed QR Code', readonly=True)
    qr_image_html = fields.Html(string='QR Code', compute='_compute_qr_image_html', sanitize=False)

    @api.depends('signed_qr_code')
    def _compute_qr_image_html(self):
        for wizard in self:
            if wizard.signed_qr_code:
                url = f'/report/barcode/?barcode_type=QR&value={quote(wizard.signed_qr_code)}&width=260&height=260'
                wizard.qr_image_html = Markup(
                    '<img src="%s" style="width:260px;height:260px;border:1px solid #ddd;padding:8px;border-radius:8px;"/>'
                ) % url
            else:
                wizard.qr_image_html = False

    def _open(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.title,
            'res_model': 'einvoice.result.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
