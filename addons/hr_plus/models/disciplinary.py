# -*- coding: utf-8 -*-
from odoo import fields, models


class DisciplinaryAction(models.Model):
    _name = "mn.hr.disciplinary.action"
    _description = "Disciplinary Action"
    _inherit = ["mail.thread"]
    _order = "incident_date desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.disciplinary.action") or "/",
        readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    issued_by_id = fields.Many2one("res.users", default=lambda s: s.env.user, tracking=True)
    incident_date = fields.Date(required=True, default=fields.Date.today, tracking=True)
    action_type = fields.Selection([
        ("verbal_warning", "Verbal warning"),
        ("written_warning", "Written warning"),
        ("final_warning", "Final warning"),
        ("suspension", "Suspension"),
        ("salary_deduction", "Salary deduction"),
        ("termination", "Termination"),
    ], required=True, default="verbal_warning", tracking=True)
    severity = fields.Selection([
        ("minor", "Minor"), ("moderate", "Moderate"),
        ("major", "Major"), ("gross", "Gross misconduct"),
    ], default="minor")
    description = fields.Text(required=True)
    employee_response = fields.Text()
    suspension_days = fields.Integer()
    deduction_amount = fields.Monetary(currency_field="currency_id")
    document = fields.Binary(attachment=True)
    employee_acknowledged = fields.Boolean(default=False, tracking=True)
    acknowledged_on = fields.Date()
    state = fields.Selection([
        ("draft", "Draft"), ("issued", "Issued"),
        ("acknowledged", "Acknowledged"), ("appealed", "Appealed"),
        ("closed", "Closed"),
    ], default="draft", tracking=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    def action_issue(self):
        self.write({"state": "issued"})
    def action_acknowledge(self):
        self.write({"state": "acknowledged", "employee_acknowledged": True,
                     "acknowledged_on": fields.Date.today()})
    def action_close(self):
        self.write({"state": "closed"})
