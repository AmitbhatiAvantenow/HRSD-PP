# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    einvoice_base_url = fields.Char(related='company_id.einvoice_base_url', readonly=False)
    einvoice_client_id = fields.Char(related='company_id.einvoice_client_id', readonly=False)
    einvoice_client_secret = fields.Char(related='company_id.einvoice_client_secret', readonly=False)
    einvoice_username = fields.Char(related='company_id.einvoice_username', readonly=False)
    einvoice_password = fields.Char(related='company_id.einvoice_password', readonly=False)
    einvoice_gstin = fields.Char(related='company_id.einvoice_gstin', readonly=False)
    einvoice_ip_address = fields.Char(related='company_id.einvoice_ip_address', readonly=False)

    einvoice_path_authenticate = fields.Char(
        related='company_id.einvoice_path_authenticate', readonly=False)
    einvoice_path_generate_irn = fields.Char(
        related='company_id.einvoice_path_generate_irn', readonly=False)
    einvoice_path_get_irn = fields.Char(
        related='company_id.einvoice_path_get_irn', readonly=False)
    einvoice_path_cancel_irn = fields.Char(
        related='company_id.einvoice_path_cancel_irn', readonly=False)
    einvoice_path_generate_ewaybill = fields.Char(
        related='company_id.einvoice_path_generate_ewaybill', readonly=False)
    einvoice_path_get_ewaybill = fields.Char(
        related='company_id.einvoice_path_get_ewaybill', readonly=False)

    einvoice_header_client_id = fields.Char(
        related='company_id.einvoice_header_client_id', readonly=False)
    einvoice_header_client_secret = fields.Char(
        related='company_id.einvoice_header_client_secret', readonly=False)
    einvoice_header_username = fields.Char(
        related='company_id.einvoice_header_username', readonly=False)
    einvoice_header_password = fields.Char(
        related='company_id.einvoice_header_password', readonly=False)
    einvoice_header_ip_address = fields.Char(
        related='company_id.einvoice_header_ip_address', readonly=False)
    einvoice_header_gstin = fields.Char(
        related='company_id.einvoice_header_gstin', readonly=False)
    einvoice_header_auth_token = fields.Char(
        related='company_id.einvoice_header_auth_token', readonly=False)
