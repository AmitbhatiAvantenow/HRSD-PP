# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    einvoice_base_url = fields.Char(
        string='e-Invoice API Base URL', default='https://apisandbox.whitebooks.in',
        help="e-Invoice GSP API host. Use the sandbox host while testing; switch "
             "to the production host once your GSP activates your live credentials. "
             "Change this (and the Advanced settings below) if you ever move to a "
             "GSP other than WhiteBooks - nothing here is hard-coded to one provider.")
    einvoice_client_id = fields.Char(string='e-Invoice Client ID')
    einvoice_client_secret = fields.Char(string='e-Invoice Client Secret')
    einvoice_username = fields.Char(string='e-Invoice API Username')
    einvoice_password = fields.Char(string='e-Invoice API Password')
    einvoice_gstin = fields.Char(
        string='e-Invoice GSTIN', help="GSTIN registered with your GSP for "
        "e-Invoicing. Defaults to the company's Tax ID (GSTIN).")
    einvoice_ip_address = fields.Char(
        string='e-Invoice Client IP', help="Public IP address to report to the "
        "e-Invoice API on every call.")

    # Cached bearer token so we don't re-authenticate on every single call.
    einvoice_auth_token = fields.Char(string='e-Invoice Auth Token', copy=False)
    einvoice_auth_token_expiry = fields.Datetime(
        string='e-Invoice Auth Token Expiry', copy=False)

    # --- Advanced: endpoint paths -----------------------------------------
    # The actual IRN JSON payload (SellerDtls/BuyerDtls/ItemList/...) follows
    # the government's standard NIC e-Invoice schema, which every GSP has to
    # support as-is - so it never needs to change here. What genuinely varies
    # GSP to GSP is the URL routing and the header names used to carry
    # credentials, which is exactly what these Advanced fields expose, so a
    # future provider switch is a Settings change, not a code change.
    einvoice_path_authenticate = fields.Char(
        string='Path: Authenticate', default='/einvoice/authenticate')
    einvoice_path_generate_irn = fields.Char(
        string='Path: Generate IRN', default='/einvoice/type/GENERATE/version/V1_03')
    einvoice_path_get_irn = fields.Char(
        string='Path: Get IRN Details', default='/einvoice/type/GETIRN/version/V1_03')
    einvoice_path_cancel_irn = fields.Char(
        string='Path: Cancel IRN', default='/einvoice/type/CANCEL/version/V1_03')
    einvoice_path_generate_ewaybill = fields.Char(
        string='Path: Generate E-Way Bill',
        default='/einvoice/type/GENERATE_EWAYBILL/version/V1_03')
    einvoice_path_get_ewaybill = fields.Char(
        string='Path: Get E-Way Bill Details',
        default='/einvoice/type/GETEWAYBILLIRN/version/V1_03')

    # --- Advanced: request header names ------------------------------------
    einvoice_header_client_id = fields.Char(string='Header: Client ID', default='client_id')
    einvoice_header_client_secret = fields.Char(
        string='Header: Client Secret', default='client_secret')
    einvoice_header_username = fields.Char(string='Header: Username', default='username')
    einvoice_header_password = fields.Char(string='Header: Password', default='password')
    einvoice_header_ip_address = fields.Char(
        string='Header: Client IP', default='ip_address')
    einvoice_header_gstin = fields.Char(string='Header: GSTIN', default='gstin')
    einvoice_header_auth_token = fields.Char(
        string='Header: Auth Token', default='auth-token')
