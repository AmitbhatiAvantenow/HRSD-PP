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

    # --- Salary Components: plain, independent numbers the admin types
    # in directly - this month's full (pre pro-ration) amount for each.
    # None of these are derived from Wage or from each other, and
    # editing one never changes any of the others - deliberately, after
    # an earlier percentage/Wage-driven auto-calc version of this proved
    # fragile (a blank field mid-edit could silently corrupt Basic, HRA,
    # CTC, etc. together). Total CTC below is the only computed field
    # here, and it's a plain sum - it can only ever reflect these, never
    # write back to them.
    basic_amount = fields.Monetary(string='Basic Salary')
    hra_cca_amount = fields.Monetary(
        string='City Compensatory Allowance + HRA')
    project_allowance_amount = fields.Monetary(
        string='Project & Special Allowance')
    epf_employee_amount = fields.Monetary(string='EPF Employee Deduction')
    epf_employer_amount = fields.Monetary(
        string='Company EPF Share (12%)')
    epf_admin_amount = fields.Monetary(
        string='EPF Exp (1%) 0.5% EDLI+ 0.5% EPF ADMIN')

    lwf_employee = fields.Monetary(
        string='LWF Employee Contribution', default=0.0,
        help="Labour Welfare Fund - employee's share, deducted from Net.")

    ctc_amount = fields.Monetary(
        string='Total CTC (Monthly)', compute='_compute_ctc_amount',
        store=True,
        help="Total Salary (Basic + CCA/HRA + Medical + Project "
             "Allowance) + Company EPF Share + EPF Exp. Purely the sum "
             "of the components to the left - to change it, change one "
             "of those.")

    @api.depends('basic_amount', 'hra_cca_amount', 'medical_allowance',
                'project_allowance_amount', 'epf_employer_amount',
                'epf_admin_amount')
    def _compute_ctc_amount(self):
        for version in self:
            total_salary = (
                (version.basic_amount or 0.0)
                + (version.hra_cca_amount or 0.0)
                + (version.medical_allowance or 0.0)
                + (version.project_allowance_amount or 0.0))
            version.ctc_amount = (
                total_salary + (version.epf_employer_amount or 0.0)
                + (version.epf_admin_amount or 0.0))

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
