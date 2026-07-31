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


class HrContract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """
    _inherit = 'hr.version'

    struct_id = fields.Many2one('hr.payroll.structure',
                                string='Salary Structure',
                                help="Choose Payroll Structure")
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', index=True, default='monthly',
        help="Defines the frequency of the wage payment.")
    hra = fields.Monetary(string='HRA', tracking=True,
                          help="House rent allowance.")
    travel_allowance = fields.Monetary(string="Travel Allowance",
                                       help="Travel allowance")
    da = fields.Monetary(string="DA", help="Dearness allowance")
    meal_allowance = fields.Monetary(string="Meal Allowance",
                                     help="Meal allowance")
    medical_allowance = fields.Monetary(string="Medical Allowance",
                                        default=1250.0,
                                        help="Fixed monthly medical allowance")
    other_allowance = fields.Monetary(string="Other Allowance",
                                      help="Other allowances")

    # --- Auto-computed salary structure (% of Gross / Basic), matching
    # a typical Indian "Basic + HRA + CCA + Medical + balancing allowance"
    # compensation structure. `wage` is used as the target Monthly Gross.
    ctc_basic_percentage = fields.Float(
        string='Basic (% of Gross)', default=50.0,
        help="Basic Salary as a percentage of the monthly Gross Wage.")
    hra_percentage_of_basic = fields.Float(
        string='HRA (% of Basic)', default=40.0,
        help="House Rent Allowance as a percentage of Basic Salary.")
    cca_percentage_of_basic = fields.Float(
        string='CCA (% of Basic)', default=20.0,
        help="City Compensatory Allowance as a percentage of Basic Salary.")

    epf_wage_ceiling = fields.Monetary(
        string='EPF Wage Ceiling', default=15000.0,
        help="Statutory monthly Basic ceiling used to compute EPF "
             "contributions (contribution is computed on min(Basic, "
             "this ceiling)).")
    epf_employee_rate = fields.Float(
        string='EPF Employee Rate (%)', default=12.0,
        help="Employee's EPF contribution, deducted from Net pay.")
    epf_employer_rate = fields.Float(
        string='EPF Employer Rate (%)', default=12.0,
        help="Employer's EPF contribution. Part of CTC, not deducted "
             "from the employee's Net pay.")
    epf_admin_rate = fields.Float(
        string='EPF Admin/EDLI Rate (%)', default=1.0,
        help="Combined EDLI + EPF administration charges paid by the "
             "employer. Part of CTC, not deducted from Net pay. This "
             "rate varies by payroll processor/period in practice - "
             "adjust it if it needs to match a specific payslip.")

    lwf_employee = fields.Monetary(
        string='LWF Employee Contribution', default=0.0,
        help="Labour Welfare Fund - employee's share, deducted from Net.")
    lwf_employer = fields.Monetary(
        string='LWF Employer Contribution', default=0.0,
        help="Labour Welfare Fund - employer's share. Part of CTC.")

    gratuity_rate = fields.Float(
        string='Gratuity Rate (%)', default=4.81,
        help="Statutory gratuity accrual, ~15/26/12 of Basic. "
             "Informational only: shown on the employee's Payroll tab, "
             "not deducted/added on the monthly payslip.")
    gratuity_per_month = fields.Monetary(
        string='Gratuity per Month', compute='_compute_gratuity_per_month')

    @api.depends('wage', 'ctc_basic_percentage', 'gratuity_rate')
    def _compute_gratuity_per_month(self):
        for version in self:
            basic = (version.wage or 0.0) * (
                version.ctc_basic_percentage or 0.0) / 100.0
            version.gratuity_per_month = basic * (
                version.gratuity_rate or 0.0) / 100.0

    # --- Full-month (non pro-rated) preview of the auto-computed
    # compensation breakdown, shown on the employee's Payroll tab so the
    # numbers are visible before a payslip is even generated.
    basic_amount = fields.Monetary(
        string='Basic Salary', compute='_compute_salary_breakdown')
    hra_amount = fields.Monetary(
        string='HRA (Auto)', compute='_compute_salary_breakdown')
    cca_amount = fields.Monetary(
        string='City Compensatory Allowance', compute='_compute_salary_breakdown')
    project_allowance_amount = fields.Monetary(
        string='Project & Special Allowance (balancing figure)',
        compute='_compute_salary_breakdown')
    epf_employee_amount = fields.Monetary(
        string='EPF Employee Deduction', compute='_compute_salary_breakdown')
    epf_employer_amount = fields.Monetary(
        string='EPF Employer Contribution', compute='_compute_salary_breakdown')
    epf_admin_amount = fields.Monetary(
        string='EPF Admin/EDLI Charges', compute='_compute_salary_breakdown')
    ctc_amount = fields.Monetary(
        string='Total CTC (Monthly)', compute='_compute_salary_breakdown')

    @api.depends('wage', 'ctc_basic_percentage', 'hra_percentage_of_basic',
                'cca_percentage_of_basic', 'medical_allowance',
                'epf_wage_ceiling', 'epf_employee_rate', 'epf_employer_rate',
                'epf_admin_rate', 'lwf_employee', 'lwf_employer',
                'gratuity_rate')
    def _compute_salary_breakdown(self):
        for version in self:
            gross = version.wage or 0.0
            basic = gross * (version.ctc_basic_percentage or 0.0) / 100.0
            hra = basic * (version.hra_percentage_of_basic or 0.0) / 100.0
            cca = basic * (version.cca_percentage_of_basic or 0.0) / 100.0
            project_allowance = gross - basic - hra - cca - (
                version.medical_allowance or 0.0)
            epf_base = min(basic, version.epf_wage_ceiling or 0.0)
            gratuity = basic * (version.gratuity_rate or 0.0) / 100.0
            version.basic_amount = basic
            version.hra_amount = hra
            version.cca_amount = cca
            version.project_allowance_amount = project_allowance
            version.epf_employee_amount = round(
                epf_base * (version.epf_employee_rate or 0.0) / 100.0, 2)
            version.epf_employer_amount = round(
                epf_base * (version.epf_employer_rate or 0.0) / 100.0, 2)
            version.epf_admin_amount = round(
                epf_base * (version.epf_admin_rate or 0.0) / 100.0, 2)
            # CTC = Gross + employer's EPF + EPF admin/EDLI + LWF employer
            # + gratuity accrual - gratuity is a real employer cost even
            # though it's only paid out at exit, so standard Indian CTC
            # definitions include it (matches the payslip's own "Total
            # CTC (this period)" rule, which folds GRATUITY into COMP).
            version.ctc_amount = (
                gross + version.epf_employer_amount
                + version.epf_admin_amount + (version.lwf_employer or 0.0)
                + round(gratuity, 2))

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by
        hierarchy (parent=False first,then first level children and so on)
        and without duplicate
        """
        # Prefer the structure set directly on the contract; fall back to
        # a linked contract template's structure for backward compatibility
        # with contracts created from a template.
        structures = self.mapped('struct_id') or self.mapped(
            'contract_template_id.struct_id')

        if not structures:
            return []
        # YTI TODO return browse records
        return list(set(structures._get_parent_structure().ids))

    def get_attribute(self, code, attribute):
        """Function for return code for Contract"""
        return self.env['hr.contract.advantage.template'].search(
                [('code', '=', code)],
                limit=1)[attribute]

    def set_attribute_value(self, code, active):
        """Function for set code for Contract"""
        for contract in self:
            if active:
                value = self.env['hr.contract.advantage.template'].search(
                    [('code', '=', code)], limit=1).default_value
                contract[code] = value
            else:
                contract[code] = 0.0
