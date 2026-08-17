# -*- coding: utf-8 -*-
import base64

from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Once an invoice's e-signature document is fully signed, every PDF
        entry point (the backend Print button, the customer Preview/portal
        route, and our own "Extended Invoice" button) should hand out the
        actual signed document instead of a freshly re-rendered unsigned
        one - they all converge on this method regardless of caller."""
        if res_ids and len(res_ids) == 1:
            report = self._get_report(report_ref)
            if report.model == 'account.move':
                move = self.env['account.move'].browse(res_ids[0])
                doc = move.esign_document_id.sudo()
                if doc and doc.state == 'completed' and doc.final_signed_file_data:
                    return base64.b64decode(doc.final_signed_file_data), 'pdf'
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
