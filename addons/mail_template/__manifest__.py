# -*- coding: utf-8 -*-
{
    'name': 'Modern Mail Templates',
    'version': '19.0.1.0.0',
    'category': 'Discuss',
    'summary': 'Modern branded HTML layout for outgoing payslip and invoice emails',
    'description': """
Modern Mail Templates
======================
Provides one reusable modern branded HTML email layout (gradient header,
wave divider, card-based content, icon footer - built from the company's
name/logo/website/email/address) and applies it to the emails this
database actually sends:

  * Payslip emails (hr_payroll_community's "Send by Email")
  * Invoice emails (account's "Invoice: Sending" template)

New email types can reuse the same layout via the
`mail.template.layout` helper model.
""",
    'author': 'HRSD-PP',
    'depends': ['mail', 'hr_payroll_community', 'account'],
    'data': [
        'data/mail_layout_templates.xml',
        'data/account_invoice_mail_template.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
