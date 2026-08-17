# -*- coding: utf-8 -*-
import base64
import hashlib
import uuid

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_layout = fields.Selection(
        [
            ('staff_augmentation', 'Staff Augmentation (Days/Hours based)'),
            ('advance_simple', 'Simple / Advance / AMC'),
        ],
        string='Extended Invoice Layout',
        default='staff_augmentation',
        help="Controls which sections and columns are printed on the "
             "Extended Invoice PDF.")

    # Consultant / assignment details
    consultant_name = fields.Char(string='Consultant / Resource Name')
    job_role = fields.Char(string='Job Role / Designation')
    service_period = fields.Char(string='Service Period', help="e.g. \"June '26\"")
    client_po_number = fields.Char(string='Client PO Number')
    invoice_subject = fields.Char(
        string='Invoice Subject',
        help="Printed under the invoice number, e.g. \"June '26 Services by "
             "Abhishek R - Purchase Order #810013986\"")

    # Bill to contact details
    kind_attn = fields.Char(string='Kind Attn')
    cc_details = fields.Text(string='CC Details')

    # Days / hours billing
    days_worked = fields.Float(string='Days Worked')
    hours_per_day = fields.Float(string='Hours per Day', default=8.0)
    hourly_rate = fields.Monetary(string='Hourly Rate', currency_field='currency_id')
    hours_worked = fields.Float(
        string='Hours Worked', compute='_compute_hours_worked', store=True)

    # Deduction / assessable value breakdown (informational, printed on the
    # extended PDF only - does not alter the accounting tax computation).
    ccw_deduction_percent = fields.Float(string='CCW Deduction (%)')
    ccw_deduction_amount = fields.Monetary(
        string='CCW Deduction Amount', compute='_compute_ccw_deduction',
        store=True, currency_field='currency_id')
    final_assessable_value = fields.Monetary(
        string='Final Assessable Value', compute='_compute_ccw_deduction',
        store=True, currency_field='currency_id')
    extended_grand_total = fields.Monetary(
        string='Extended Total Payable', compute='_compute_ccw_deduction',
        store=True, currency_field='currency_id',
        help="Final Assessable Value + Taxes. Matches the accounting total "
             "unless a CCW deduction is applied, in which case it reflects "
             "the net amount payable shown on the Extended Invoice PDF.")

    # Export / compliance details
    is_export_under_lut = fields.Boolean(
        string='Supply under LUT (Export without IGST)')
    lut_arn = fields.Char(string='LUT ARN')
    reverse_charge_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Reverse Charge Applicable', default='no')

    invoice_reference_hash = fields.Char(
        string='Invoice Reference Number', copy=False, readonly=True)

    # Authorized signatory, defaulted from the company but editable per invoice
    authorized_signatory_name = fields.Char(
        string='Authorized Signatory', compute='_compute_signatory',
        store=True, readonly=False)
    authorized_signatory_designation = fields.Char(
        string='Signatory Designation', compute='_compute_signatory',
        store=True, readonly=False)

    esign_document_id = fields.Many2one(
        'hr.esign.document', string='E-Sign Document', copy=False, readonly=True)
    esign_state = fields.Selection(
        [
            ('not_sent', 'Not Sent'),
            ('pending', 'Pending on Sign'),
            ('signed', 'Signed'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
        ],
        string='Signature Status', compute='_compute_esign_state')

    @api.depends('esign_document_id.state')
    def _compute_esign_state(self):
        pending_states = {'draft', 'sent', 'in_progress', 'archived'}
        for move in self:
            doc_state = move.esign_document_id.state
            if not doc_state:
                move.esign_state = 'not_sent'
            elif doc_state == 'completed':
                move.esign_state = 'signed'
            elif doc_state in pending_states:
                move.esign_state = 'pending'
            else:
                move.esign_state = doc_state

    @api.depends('days_worked', 'hours_per_day')
    def _compute_hours_worked(self):
        for move in self:
            move.hours_worked = move.days_worked * move.hours_per_day

    def _sync_staff_aug_pricing(self):
        """Days Worked / Hourly Rate are printed on the Extended Invoice PDF,
        but they used to be pure display fields with no link to the actual
        invoice line — so the printed hours/rate and the real invoiced amount
        could show unrelated numbers. When there's a single product line,
        drive its quantity/price from these fields instead, the same way the
        reference invoice format computes Total Cost = Hourly Rate x Hours.
        Called on save (not as a live onchange — an onchange here doesn't
        reliably propagate to the sibling Invoice Lines list in this view)."""
        for move in self:
            if move.invoice_layout != 'staff_augmentation':
                continue
            product_lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            if len(product_lines) == 1 and (
                product_lines.quantity != move.hours_worked
                or product_lines.price_unit != move.hourly_rate
            ):
                product_lines.write({
                    'quantity': move.hours_worked,
                    'price_unit': move.hourly_rate,
                })

    @api.depends('amount_untaxed', 'amount_tax', 'ccw_deduction_percent', 'invoice_layout')
    def _compute_ccw_deduction(self):
        for move in self:
            percent = move.ccw_deduction_percent if move.invoice_layout == 'staff_augmentation' else 0.0
            amount = percent / 100.0 * move.amount_untaxed
            move.ccw_deduction_amount = amount
            move.final_assessable_value = move.amount_untaxed - amount
            move.extended_grand_total = move.final_assessable_value + move.amount_tax

    @api.depends('company_id')
    def _compute_signatory(self):
        for move in self:
            move.authorized_signatory_name = move.company_id.invoice_signatory_name
            move.authorized_signatory_designation = move.company_id.invoice_signatory_designation

    def action_print_extended_invoice(self):
        """Print the Extended Invoice — the fully-signed copy once one exists,
        otherwise a freshly-rendered PDF."""
        self.ensure_one()
        doc = self.esign_document_id.sudo()
        if doc and doc.state == 'completed' and doc.final_signed_file_data:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/hrsd/sign/document/{doc.id}/download',
                'target': 'self',
            }
        report = self.env.ref('invoicing_extended.action_report_invoice_extended')
        return report.report_action(self, config=False)

    def action_send_for_signature(self):
        """Open the HR Sign "Create Document" wizard with this invoice's
        Extended Invoice PDF pre-loaded as the document to sign, and the
        invoice's customer pre-filled as the signer."""
        self.ensure_one()
        report = self.env.ref('invoicing_extended.action_report_invoice_extended')
        pdf_content, _report_type = report._render_qweb_pdf(report.report_name, [self.id])
        return {
            'type': 'ir.actions.client',
            'tag': 'hr_esign_create_wizard',
            'name': _('Send for Signature'),
            'target': 'new',
            'params': {
                'prefill': {
                    'title': self.invoice_subject or self.display_name,
                    'fileData': base64.b64encode(pdf_content).decode(),
                    'fileName': f"{self.name or 'Invoice'}.pdf",
                    'partnerId': self.partner_id.id,
                    'partnerName': self.partner_id.name,
                    'partnerEmail': self.partner_id.email or '',
                    'originModel': 'account.move',
                    'originId': self.id,
                    'originField': 'esign_document_id',
                },
            },
        }

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.move_type in ('out_invoice', 'out_refund') and self.invoice_layout:
            return 'invoicing_extended.report_invoice_extended_document'
        return super()._get_name_invoice_report()

    def _signed_invoice_document(self):
        """The signed PDF, as a legal-document dict, once the e-signature is
        complete - or False otherwise. Both `_get_invoice_legal_documents`
        and `_get_invoice_legal_documents_all` below fetch a *cached*
        ir.attachment (see `invoice_pdf_report_id`) rather than re-rendering,
        which is what the portal's "Download" button and other legal-document
        consumers actually call - overriding `_render_qweb_pdf` alone (which
        covers Print/Preview) doesn't reach that cache-lookup path."""
        self.ensure_one()
        doc = self.esign_document_id.sudo()
        if doc and doc.state == 'completed' and doc.final_signed_file_data:
            return {
                'filename': doc.final_signed_file_name or self._get_invoice_report_filename(),
                'filetype': 'application/pdf',
                'content': base64.b64decode(doc.final_signed_file_data),
            }
        return False

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        self.ensure_one()
        if filetype == 'pdf':
            signed = self._signed_invoice_document()
            if signed:
                return signed
        return super()._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback)

    def _get_invoice_legal_documents_all(self, allow_fallback=False):
        self.ensure_one()
        signed = self._signed_invoice_document()
        if signed:
            return [signed]
        return super()._get_invoice_legal_documents_all(allow_fallback=allow_fallback)

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.is_invoice() and not move.invoice_reference_hash:
                move.invoice_reference_hash = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
            if (move.is_invoice() and not move.ccw_deduction_percent
                    and move.invoice_layout == 'staff_augmentation'):
                move.ccw_deduction_percent = move.company_id.invoice_default_ccw_percent
            if move.is_invoice() and not move.lut_arn:
                move.lut_arn = move.company_id.invoice_default_lut_arn
        moves._sync_staff_aug_pricing()
        return moves

    _STAFF_AUG_PRICING_TRIGGERS = {
        'days_worked', 'hours_per_day', 'hourly_rate', 'invoice_layout', 'invoice_line_ids',
    }

    def write(self, vals):
        res = super().write(vals)
        if self._STAFF_AUG_PRICING_TRIGGERS & set(vals.keys()):
            self._sync_staff_aug_pricing()
        return res
