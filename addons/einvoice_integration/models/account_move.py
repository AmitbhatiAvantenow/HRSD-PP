# -*- coding: utf-8 -*-
import json
import re
from datetime import datetime
from urllib.parse import quote

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .einvoice_api import EInvoiceApiError, WhitebooksEInvoiceClient, _find_key

EINVOICE_CANCEL_REASONS = [
    ('1', 'Duplicate'),
    ('2', 'Data Entry Mistake'),
    ('3', 'Order Cancelled'),
    ('4', 'Other'),
]


def _digits(value):
    return re.sub(r'\D', '', value or '')


class AccountMove(models.Model):
    _inherit = 'account.move'

    einvoice_status = fields.Selection(
        [
            ('not_generated', 'Not Generated'),
            ('generated', 'Generated'),
            ('cancelled', 'Cancelled'),
        ],
        string='e-Invoice Status', default='not_generated', copy=False, tracking=True)
    einvoice_irn = fields.Char(string='IRN', copy=False, readonly=True)
    einvoice_ack_no = fields.Char(string='Ack No', copy=False, readonly=True)
    einvoice_ack_date = fields.Datetime(string='Ack Date', copy=False, readonly=True)
    einvoice_signed_qr_code = fields.Text(string='Signed QR Code', copy=False, readonly=True)
    einvoice_qr_image_html = fields.Html(
        string='e-Invoice QR Code', compute='_compute_einvoice_qr_image_html', sanitize=False)
    einvoice_cancel_reason = fields.Selection(
        EINVOICE_CANCEL_REASONS, string='e-Invoice Cancel Reason', copy=False, readonly=True)
    einvoice_cancel_remarks = fields.Char(string='e-Invoice Cancel Remarks', copy=False, readonly=True)
    einvoice_cancel_date = fields.Datetime(string='e-Invoice Cancel Date', copy=False, readonly=True)
    einvoice_ewaybill_no = fields.Char(string='E-Way Bill No', copy=False, readonly=True)
    einvoice_ewaybill_date = fields.Datetime(string='E-Way Bill Date', copy=False, readonly=True)
    einvoice_ewaybill_valid_upto = fields.Datetime(
        string='E-Way Bill Valid Upto', copy=False, readonly=True)
    einvoice_error = fields.Text(string='e-Invoice Last Error', copy=False, readonly=True)

    @api.depends('einvoice_signed_qr_code')
    def _compute_einvoice_qr_image_html(self):
        for move in self:
            if move.einvoice_signed_qr_code:
                url = (f'/report/barcode/?barcode_type=QR&value='
                       f'{quote(move.einvoice_signed_qr_code)}&width=220&height=220')
                move.einvoice_qr_image_html = Markup(
                    '<img src="%s" style="width:220px;height:220px;border:1px solid #ddd;'
                    'padding:6px;border-radius:8px;"/>'
                ) % url
            else:
                move.einvoice_qr_image_html = False

    # ------------------------------------------------------------------
    # JSON payload builder (NIC IRP schema)
    # ------------------------------------------------------------------
    def _einvoice_partner_details(self, partner, is_buyer=False, gstin_override=None):
        self.ensure_one()
        zip_digits = _digits(partner.zip)
        details = {
            'Addr1': partner.street or '',
            'Loc': partner.city or '',
            'Stcd': partner.state_id.l10n_in_tin or '',
            'LglNm': partner.commercial_partner_id.name or partner.name or '',
            'TrdNm': partner.name or '',
            'Gstin': gstin_override or partner.vat or 'URP',
        }
        if zip_digits:
            details['Pin'] = int(zip_digits)
        if partner.street2:
            details['Addr2'] = partner.street2
        if partner.email:
            details['Em'] = partner.email
        phone_digits = _digits(partner.phone)
        if phone_digits:
            details['Ph'] = phone_digits[-10:]
        if is_buyer:
            details['Pos'] = (self.l10n_in_state_id.l10n_in_tin
                               or partner.state_id.l10n_in_tin or '')
        return details

    def _einvoice_line_gst_breakdown(self, line):
        self.ensure_one()
        base = line.price_unit * line.quantity * (1 - (line.discount or 0.0) / 100.0)
        taxes_res = line.tax_ids.compute_all(
            base, currency=line.currency_id, quantity=1,
            product=line.product_id, partner=line.partner_id)
        breakdown = {
            'cgst_rate': 0.0, 'cgst_amt': 0.0,
            'sgst_rate': 0.0, 'sgst_amt': 0.0,
            'igst_rate': 0.0, 'igst_amt': 0.0,
        }
        for tax_res in taxes_res['taxes']:
            tax = self.env['account.tax'].browse(tax_res['id'])
            gst_type = tax.l10n_in_gst_tax_type
            if gst_type == 'igst':
                breakdown['igst_rate'] += tax.amount
                breakdown['igst_amt'] += tax_res['amount']
            elif gst_type == 'cgst':
                breakdown['cgst_rate'] += tax.amount
                breakdown['cgst_amt'] += tax_res['amount']
            elif gst_type == 'sgst':
                breakdown['sgst_rate'] += tax.amount
                breakdown['sgst_amt'] += tax_res['amount']
        return breakdown, taxes_res['total_excluded']

    def _einvoice_item_list(self):
        self.ensure_one()
        items = []
        missing_hsn = []
        product_lines = self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        for index, line in enumerate(product_lines, start=1):
            if not line.l10n_in_hsn_code:
                missing_hsn.append(line.name or _('line %s') % index)
                continue
            breakdown, assessable = self._einvoice_line_gst_breakdown(line)
            gst_rate = breakdown['igst_rate'] or (breakdown['cgst_rate'] + breakdown['sgst_rate'])
            quantity = line.quantity or 0.0
            # UnitPrice/TotAmt must be the *gross* (pre-discount) price: the
            # IRP requires AssAmt == TotAmt - Discount, so deriving UnitPrice
            # from the already-discounted `assessable` value (as before) made
            # Discount get subtracted twice and failed that check on any line
            # with a discount.
            unit_price = line.price_unit
            hsn_digits = _digits(line.l10n_in_hsn_code) or line.l10n_in_hsn_code
            item = {
                'SlNo': str(index),
                # SAC (service) codes always start with "99" under GST - that
                # prefix is the authoritative signal, not the Odoo product's
                # own type (which can be set inconsistently with its HSN).
                'IsServc': 'Y' if hsn_digits.startswith('99') else 'N',
                'HsnCd': hsn_digits,
                'Qty': round(quantity, 3) or 1,
                'Unit': (line.product_uom_id.l10n_in_code or 'OTH').split('-')[0],
                'UnitPrice': round(unit_price, 3),
                'TotAmt': round(unit_price * quantity, 2),
                'Discount': round((unit_price * quantity) * ((line.discount or 0.0) / 100.0), 2),
                'AssAmt': round(assessable, 2),
                'GstRt': round(gst_rate, 2),
                'CgstAmt': round(breakdown['cgst_amt'], 2),
                'SgstAmt': round(breakdown['sgst_amt'], 2),
                'IgstAmt': round(breakdown['igst_amt'], 2),
                'CesRt': 0,
                'CesAmt': 0,
                'CesNonAdvlAmt': 0,
                'OthChrg': 0,
                'TotItemVal': round(
                    assessable + breakdown['cgst_amt'] + breakdown['sgst_amt']
                    + breakdown['igst_amt'], 2),
            }
            if line.name:
                item['PrdDesc'] = line.name.replace('\n', ' ')[:300]
            items.append(item)
        if missing_hsn:
            raise UserError(_(
                "These invoice lines have no HSN/SAC Code, which the e-Invoice "
                "API requires: %(lines)s", lines=', '.join(missing_hsn)))
        if not items:
            raise UserError(_("This invoice has no product lines to submit for e-Invoicing."))
        return items

    @api.model
    def _check_einvoice_address(self, partner, who):
        if not (partner.street and partner.city and partner.zip and partner.state_id):
            raise UserError(_(
                "%(who)s's address is incomplete (street, city, PIN code and state "
                "are all required by the e-Invoice API). Fill it in on the contact's "
                "record.", who=who))
        if not partner.state_id.l10n_in_tin:
            raise UserError(_(
                "%(who)s's state (%(state)s) has no GST state code (TIN) configured.",
                who=who, state=partner.state_id.name))

    def _einvoice_supply_type(self):
        """Map the invoice's GST Treatment to the IRP's Type of Supply code.
        e-Invoicing under GST only applies to B2B, export, SEZ and
        deemed-export sales - a plain B2C/consumer sale has no valid
        SupTyp at all, so that case is rejected here with a clear reason
        instead of sending a value ("B2C") the API will reject anyway."""
        self.ensure_one()
        treatment = self.l10n_in_gst_treatment
        if treatment in ('regular', 'uin_holders'):
            return 'B2B'
        if treatment == 'deemed_export':
            return 'DEXP'
        if treatment in ('special_economic_zone', 'overseas'):
            is_lut = bool(self.invoice_line_ids.tax_ids.filtered('l10n_in_is_lut'))
            prefix = 'SEZ' if treatment == 'special_economic_zone' else 'EXP'
            return f'{prefix}WOP' if is_lut else f'{prefix}WP'
        treatment_label = dict(
            self._fields['l10n_in_gst_treatment'].selection).get(treatment, treatment or _('not set'))
        raise UserError(_(
            "e-Invoicing only applies to B2B sales (registered business "
            "customers with a GSTIN), exports, SEZ or deemed-export sales. "
            "This invoice's customer (%(partner)s) has GST Treatment "
            "\"%(treatment)s\", so it isn't eligible for e-Invoice generation.",
            partner=self.partner_id.name, treatment=treatment_label))

    def _build_einvoice_json(self):
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id.commercial_partner_id or self.partner_id
        seller = company.partner_id
        self._check_einvoice_address(seller, _("Your company"))
        sup_typ = self._einvoice_supply_type()
        self._check_einvoice_address(partner, _("The customer"))
        item_list = self._einvoice_item_list()
        cgst_total = sum(i['CgstAmt'] for i in item_list)
        sgst_total = sum(i['SgstAmt'] for i in item_list)
        igst_total = sum(i['IgstAmt'] for i in item_list)
        assessable_total = sum(i['AssAmt'] for i in item_list)
        return {
            'Version': '1.1',
            'TranDtls': {
                'TaxSch': 'GST',
                'SupTyp': sup_typ,
                'RegRev': 'Y' if self.invoice_line_ids.tax_ids.filtered(
                    'l10n_in_reverse_charge') else 'N',
                'IgstOnIntra': 'N',
            },
            'DocDtls': {
                'Typ': 'CRN' if self.move_type == 'out_refund' else 'INV',
                'No': self.name,
                'Dt': (self.invoice_date or fields.Date.context_today(self)).strftime('%d/%m/%Y'),
            },
            'SellerDtls': self._einvoice_partner_details(
                company.partner_id,
                gstin_override=company.einvoice_gstin or company.vat),
            'BuyerDtls': self._einvoice_partner_details(partner, is_buyer=True),
            'ItemList': item_list,
            'ValDtls': {
                'AssVal': round(assessable_total, 2),
                'CgstVal': round(cgst_total, 2),
                'SgstVal': round(sgst_total, 2),
                'IgstVal': round(igst_total, 2),
                'CesVal': 0,
                'StCesVal': 0,
                'Discount': 0,
                'OthChrg': 0,
                'RndOffAmt': round(self.amount_total - (
                    assessable_total + cgst_total + sgst_total + igst_total), 2),
                'TotInvVal': round(self.amount_total, 2),
            },
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _einvoice_client(self):
        return WhitebooksEInvoiceClient(self.company_id)

    def _einvoice_log_chatter(self, title, request_json=None, response_json=None):
        self.ensure_one()
        attachments = []
        if request_json is not None:
            attachments.append((
                f'{title} - Request.json',
                json.dumps(request_json, indent=2, default=str).encode(),
            ))
        if response_json is not None:
            attachments.append((
                f'{title} - Response.json',
                json.dumps(response_json, indent=2, default=str).encode(),
            ))
        self.message_post(body=title, attachments=attachments)

    def action_generate_einvoice(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("Only posted invoices can be submitted for e-Invoicing."))
        if self.einvoice_status == 'generated':
            raise UserError(_(
                "This invoice already has an IRN (%s). Cancel it first if you need "
                "to regenerate.") % self.einvoice_irn)
        payload = self._build_einvoice_json()
        client = self._einvoice_client()
        try:
            response = client.generate_irn(payload)
        except EInvoiceApiError as exc:
            self.einvoice_error = str(exc)
            self._einvoice_log_chatter(_('e-Invoice generation failed'), request_json=payload)
            raise
        irn = _find_key(response, 'irn')
        ack_no = _find_key(response, 'ackno')
        ack_date = _find_key(response, 'ackdt', 'ackdate')
        qr_code = _find_key(response, 'signedqrcode', 'qrcode')
        self.write({
            'einvoice_status': 'generated',
            'einvoice_irn': irn,
            'einvoice_ack_no': ack_no,
            'einvoice_ack_date': self._einvoice_parse_datetime(ack_date),
            'einvoice_signed_qr_code': qr_code,
            'einvoice_error': False,
        })
        self._einvoice_log_chatter(
            _('e-Invoice generated (IRN: %s)') % (irn or ''),
            request_json=payload, response_json=response)
        return self.env['einvoice.result.wizard'].create({
            'move_id': self.id,
            'title': _('e-Invoice Generated'),
            'irn': irn,
            'ack_no': ack_no,
            'ack_date': self.einvoice_ack_date,
            'signed_qr_code': qr_code,
        })._open()

    def action_refresh_einvoice_status(self):
        self.ensure_one()
        if not self.einvoice_irn:
            raise UserError(_("No IRN has been generated for this invoice yet."))
        client = self._einvoice_client()
        response = client.get_irn_details(self.einvoice_irn)
        self._einvoice_log_chatter(_('e-Invoice status refreshed'), response_json=response)
        status = (_find_key(response, 'status') or '').upper()
        if status in ('CNL', 'CANCELLED'):
            self.einvoice_status = 'cancelled'

    def action_open_einvoice_cancel_wizard(self):
        self.ensure_one()
        if not self.einvoice_irn or self.einvoice_status != 'generated':
            raise UserError(_("There is no active e-Invoice to cancel on this invoice."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel e-Invoice'),
            'res_model': 'einvoice.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }

    def action_open_einvoice_ewaybill_wizard(self):
        self.ensure_one()
        if not self.einvoice_irn or self.einvoice_status != 'generated':
            raise UserError(_(
                "Generate the e-Invoice (IRN) before generating an E-Way Bill for it."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate E-Way Bill'),
            'res_model': 'einvoice.ewaybill.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }

    @api.model
    def _einvoice_parse_datetime(self, value):
        """Ack/cancel timestamps come back from WhiteBooks as IST wall-clock
        strings in one of a couple of common formats; stored as-is (Odoo
        datetime fields are naive/UTC, so this is a reference value, not
        used in any date arithmetic)."""
        if not value:
            return False
        for fmt in ('%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%d-%m-%Y %H:%M:%S'):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return False
