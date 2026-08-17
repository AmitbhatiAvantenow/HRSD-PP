# -*- coding: utf-8 -*-
from odoo import _, fields, models

from ..models.einvoice_api import EInvoiceApiError, _find_key
from ..models.account_move import EINVOICE_CANCEL_REASONS


class EinvoiceCancelWizard(models.TransientModel):
    _name = 'einvoice.cancel.wizard'
    _description = 'Cancel e-Invoice (IRN)'

    move_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
    irn = fields.Char(related='move_id.einvoice_irn', string='IRN', readonly=True)
    reason = fields.Selection(EINVOICE_CANCEL_REASONS, string='Cancellation Reason', required=True)
    remarks = fields.Char(string='Remarks', required=True)

    def action_confirm(self):
        self.ensure_one()
        move = self.move_id
        client = move._einvoice_client()
        try:
            response = client.cancel_irn(move.einvoice_irn, self.reason, self.remarks)
        except EInvoiceApiError as exc:
            move.einvoice_error = str(exc)
            move._einvoice_log_chatter(
                _('e-Invoice cancellation failed'),
                request_json={'Irn': move.einvoice_irn, 'CnlRsn': self.reason, 'CnlRem': self.remarks})
            raise

        cancel_date = _find_key(response, 'canceldate', 'cnldate') or fields.Datetime.now()
        move.write({
            'einvoice_status': 'cancelled',
            'einvoice_cancel_reason': self.reason,
            'einvoice_cancel_remarks': self.remarks,
            'einvoice_cancel_date': move._einvoice_parse_datetime(cancel_date) or fields.Datetime.now(),
            'einvoice_error': False,
        })
        move._einvoice_log_chatter(
            _('e-Invoice cancelled (IRN: %s)') % move.einvoice_irn,
            request_json={'Irn': move.einvoice_irn, 'CnlRsn': self.reason, 'CnlRem': self.remarks},
            response_json=response)
        return {'type': 'ir.actions.act_window_close'}
