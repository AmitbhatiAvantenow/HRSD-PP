# -*- coding: utf-8 -*-
{
    'name': 'e-Invoice Integration (WhiteBooks GSP)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Generate, cancel and track GST e-Invoices (IRN/QR/E-Way Bill) via the WhiteBooks GSP API',
    'description': """
e-Invoice Integration (WhiteBooks GSP)
=======================================
Connects Invoicing directly to the WhiteBooks e-Invoice API (GST IRP)
so customer invoices can be submitted for e-Invoicing without leaving
Odoo:

* Company-level settings for the WhiteBooks Client ID/Secret, API
  username/password and GSTIN (sandbox or production).
* "Generate e-Invoice" button on posted customer invoices - builds the
  IRP JSON payload from the invoice's real lines/taxes/partner, calls
  Authenticate + Generate IRN, and shows the result (IRN, Ack No/Date,
  QR code) in a popup.
* IRN, Ack No/Date, signed QR code (rendered as an actual scannable
  QR image) and status are stored and shown on the invoice.
* "Cancel e-Invoice" wizard (reason + remarks) calling the Cancel IRN
  endpoint.
* "Generate E-Way Bill" wizard (transporter/vehicle details) calling
  the Generate E-Way Bill endpoint, once an IRN exists.
* Every request/response is logged to the invoice's chatter as a JSON
  attachment for a full audit trail.
    """,
    'author': 'HRSD',
    'license': 'LGPL-3',
    'depends': ['account', 'l10n_in'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'wizard/einvoice_cancel_wizard_views.xml',
        'wizard/einvoice_ewaybill_wizard_views.xml',
        'wizard/einvoice_result_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
