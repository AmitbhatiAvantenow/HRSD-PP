# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HRLetter(models.Model):
    _name = "mn.hr.letter"
    _description = "HR Letter (Experience, Salary cert, NOC, Employment)"
    _inherit = ["mail.thread"]
    _order = "issue_date desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.letter") or "/",
        readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    issue_date = fields.Date(default=fields.Date.today, required=True, tracking=True)
    letter_type = fields.Selection([
        ("employment", "Employment letter / proof"),
        ("experience", "Experience certificate"),
        ("salary_cert", "Salary certificate"),
        ("noc", "NOC (No Objection)"),
        ("visa_support", "Visa support letter"),
        ("bank_account", "Bank account opening letter"),
        ("school", "School admission letter"),
        ("travel", "Travel letter"),
        ("other", "Other"),
    ], required=True, default="employment", tracking=True)
    addressed_to = fields.Char(help="To whom the letter is addressed.")
    purpose = fields.Char()
    include_salary = fields.Boolean(default=False,
        help="Whether to disclose the salary amount on the letter.")
    salary_amount = fields.Monetary(currency_field="currency_id")
    custom_body = fields.Html(
        help="Optional custom body. Leave blank to use the default template per letter_type.")
    state = fields.Selection([
        ("draft", "Draft"), ("issued", "Issued"),
        ("printed", "Printed"), ("delivered", "Delivered"),
    ], default="draft", tracking=True)
    issued_by_id = fields.Many2one("res.users", default=lambda s: s.env.user)
    signature = fields.Binary(attachment=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    def action_issue(self): self.write({"state": "issued"})
    def action_print(self):
        self.write({"state": "printed"})
        return self.env.ref("mn_hr_plus.action_report_letter").report_action(self)
