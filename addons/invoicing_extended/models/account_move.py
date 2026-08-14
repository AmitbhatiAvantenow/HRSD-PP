# -*- coding: utf-8 -*-
import hashlib
import uuid

from odoo import api, fields, models


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

    @api.depends('days_worked', 'hours_per_day')
    def _compute_hours_worked(self):
        for move in self:
            move.hours_worked = move.days_worked * move.hours_per_day

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
        return moves
