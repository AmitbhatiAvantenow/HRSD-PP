# -*- coding: utf-8 -*-
from odoo import _, fields, models

from ..models.einvoice_api import EInvoiceApiError, _find_key

TRANSPORT_MODES = [
    ('1', 'Road'),
    ('2', 'Rail'),
    ('3', 'Air'),
    ('4', 'Ship'),
]

VEHICLE_TYPES = [
    ('R', 'Regular'),
    ('O', 'Over Dimensional Cargo'),
]


class EinvoiceEwaybillWizard(models.TransientModel):
    _name = 'einvoice.ewaybill.wizard'
    _description = 'Generate E-Way Bill'

    move_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
    irn = fields.Char(related='move_id.einvoice_irn', string='IRN', readonly=True)
    distance = fields.Integer(string='Distance (km)', required=True)
    trans_mode = fields.Selection(TRANSPORT_MODES, string='Mode of Transport', required=True, default='1')
    transporter_id = fields.Char(string="Transporter's GSTIN")
    transporter_name = fields.Char(string="Transporter's Name")
    vehicle_no = fields.Char(string='Vehicle Number')
    vehicle_type = fields.Selection(VEHICLE_TYPES, string='Vehicle Type', default='R')
    trans_doc_no = fields.Char(string='Transporter Doc No')
    trans_doc_date = fields.Date(string='Transporter Doc Date')

    def action_confirm(self):
        self.ensure_one()
        move = self.move_id
        payload = {
            'Irn': move.einvoice_irn,
            'Distance': self.distance,
            'TransMode': self.trans_mode,
            'TransId': self.transporter_id or '',
            'TransName': self.transporter_name or '',
            'VehNo': self.vehicle_no or '',
            'VehType': self.vehicle_type or 'R',
        }
        if self.trans_doc_no:
            payload['TransDocNo'] = self.trans_doc_no
        if self.trans_doc_date:
            payload['TransDocDt'] = self.trans_doc_date.strftime('%d/%m/%Y')

        client = move._einvoice_client()
        try:
            response = client.generate_ewaybill(payload)
        except EInvoiceApiError as exc:
            move.einvoice_error = str(exc)
            move._einvoice_log_chatter(_('E-Way Bill generation failed'), request_json=payload)
            raise

        ewb_no = _find_key(response, 'ewaybillno', 'ewbno')
        ewb_date = _find_key(response, 'ewaybilldate', 'ewbdt')
        valid_upto = _find_key(response, 'validupto', 'ewbvaliditydate')
        move.write({
            'einvoice_ewaybill_no': ewb_no,
            'einvoice_ewaybill_date': move._einvoice_parse_datetime(ewb_date),
            'einvoice_ewaybill_valid_upto': move._einvoice_parse_datetime(valid_upto),
            'einvoice_error': False,
        })
        move._einvoice_log_chatter(
            _('E-Way Bill generated (No: %s)') % (ewb_no or ''),
            request_json=payload, response_json=response)
        return {'type': 'ir.actions.act_window_close'}
