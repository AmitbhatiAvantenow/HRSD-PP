# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslipMailTemplate(models.Model):
    _name = 'hr.payslip.mail.template'
    _description = 'Payslip Email Template'

    # Singleton-style config record: there is only ever one, fetched (and
    # created with these defaults on first use) via get_or_create() below.
    # Edited from the New Payslip wizard's "Manage Template" button.
    subject = fields.Char(
        string='Subject', default='Your Payslip for {{month}}')
    body = fields.Text(
        string='Body',
        default=(
            "Dear {{employee_name}},\n\n"
            "Please find attached your payslip for {{month}}.\n\n"
            "Net Pay: {{net_pay}}\n\n"
            "Regards,\n{{company_name}} HR Team"
        ))
    cc = fields.Char(
        string='CC',
        help='Comma-separated email addresses to CC on every payslip '
             'email, e.g. hr@company.com, payroll@company.com')

    @api.model
    def get_or_create(self):
        """Return the single shared template record, creating it with
        its field defaults on first use."""
        template = self.search([], limit=1)
        return template if template else self.create({})

    @api.model
    def get_template_values(self):
        """Dict form of get_or_create(), for the wizard's "Manage
        Template" panel - one ORM round-trip instead of create-then-read."""
        template = self.get_or_create()
        return {
            'id': template.id,
            'subject': template.subject or '',
            'body': template.body or '',
            'cc': template.cc or '',
        }
