# -*- coding: utf-8 -*-
{
    'name': 'Invoicing Extended',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Custom staff-augmentation invoice format, fields and modern PDF template',
    'description': """
Invoicing Extended
===================
Extends the standard Invoicing (account) app for staff-augmentation /
consulting companies that bill clients based on consultant days/hours
worked, and also raise simpler advance/AMC invoices.

Adds consultant/job/service-period/PO fields, Kind Attn and CC details,
LUT-export and reverse-charge details, a CCW deduction and assessable
value breakdown, an auto-generated invoice reference number, company
level defaults (signatory, signature, LUT ARN, CCW %, tagline), an IFSC
code field on bank accounts, and a modern branded "Extended Invoice" PDF
report matching the company's own invoice format, in any currency
(INR, USD, EUR, AED, ...).
    """,
    'author': 'HRSD',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/res_company_views.xml',
        'views/res_partner_bank_views.xml',
        'views/account_move_views.xml',
        'report/invoice_extended_templates.xml',
        'report/invoice_extended_reports.xml',
    ],
    'installable': True,
    'application': False,
}
