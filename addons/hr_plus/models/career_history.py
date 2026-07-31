# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CareerHistory(models.Model):
    _name = "mn.hr.career.history"
    _description = "Employee Career History"
    _inherit = ["mail.thread"]
    _order = "effective_date desc"

    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    effective_date = fields.Date(required=True, default=fields.Date.today, tracking=True)
    change_type = fields.Selection([
        ("hire", "Hire"),
        ("promotion", "Promotion"),
        ("transfer", "Transfer / move"),
        ("salary", "Salary change"),
        ("job_title", "Job-title change"),
        ("department", "Department change"),
        ("contract_renewal", "Contract renewal"),
        ("end", "Employment end"),
    ], required=True, default="promotion", tracking=True)
    previous_job_title = fields.Char()
    new_job_title = fields.Char()
    previous_department_id = fields.Many2one("hr.department")
    new_department_id = fields.Many2one("hr.department")
    previous_salary = fields.Monetary(currency_field="currency_id")
    new_salary = fields.Monetary(currency_field="currency_id")
    increment_pct = fields.Float(compute="_compute_increment", store=True)
    reason = fields.Text()
    approved_by_id = fields.Many2one("res.users", tracking=True)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)

    @api.depends("previous_salary", "new_salary")
    def _compute_increment(self):
        for r in self:
            r.increment_pct = (((r.new_salary - r.previous_salary) / r.previous_salary) * 100
                                if r.previous_salary else 0)
