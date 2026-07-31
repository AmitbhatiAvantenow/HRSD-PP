# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class HrSalaryRule(models.Model):
    """Extends the standard 'hr.salary.rule' model to include additional
    fields for defining salary rules."""
    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account',
                                          help="Analytic account associated "
                                               "with the record")
    account_tax_id = fields.Many2one('account.tax', string='Tax',
                                     help="Tax account associated with the "
                                          "record")
    account_debit_id = fields.Many2one('account.account',
                                       string='Debit Account',
                                       help="Debit account associated with the"
                                            " record")
    account_credit_id = fields.Many2one('account.account',
                                        string='Credit Account',
                                        help="Credit account associated with"
                                             " the record")

    @api.model
    def _hr_payroll_community_set_default_accounts(self):
        """Give the 'Net Salary' rule of hr_payroll_community's "India:
        Regular Pay" structure a simple, safe accounting default (Debit
        a generic Expense account / Credit a generic Payable account for
        the company) so a fresh install can validate a payslip without
        first doing a manual accounting setup pass.

        This is a deliberately simplified single-line mapping (booked
        against Net Salary only). For a granular breakdown - separate
        EPF/LWF payable accounts, a dedicated Salaries expense account,
        etc. - set Debit/Credit on the individual rules yourself; this
        only fills in something reasonable if nothing is configured yet.
        """
        rule = self.env.ref(
            'hr_payroll_community.hr_rule_net', raise_if_not_found=False)
        if not rule or rule.account_debit_id or rule.account_credit_id:
            return
        company = self.env.company
        Account = self.env['account.account']
        expense_account = Account.search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', company.id),
            ('name', 'ilike', 'salar'),
        ], limit=1) or Account.search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', company.id),
        ], limit=1)
        payable_account = Account.search([
            ('account_type', '=', 'liability_payable'),
            ('company_ids', 'in', company.id),
        ], limit=1)
        if expense_account and payable_account:
            rule.write({
                'account_debit_id': expense_account.id,
                'account_credit_id': payable_account.id,
            })
