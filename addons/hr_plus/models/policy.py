# -*- coding: utf-8 -*-
from odoo import fields, models


class HRPolicy(models.Model):
    _name = "mn.hr.policy"
    _description = "Company Policy / Handbook"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    name_ar = fields.Char(string="Name (Arabic)")
    category = fields.Selection([
        ("handbook", "Employee handbook"),
        ("code_of_conduct", "Code of conduct"),
        ("it", "IT acceptable use"),
        ("security", "Information security"),
        ("travel", "Travel policy"),
        ("expense", "Expense policy"),
        ("leave", "Leave policy"),
        ("attendance", "Attendance policy"),
        ("conflict", "Conflict of interest"),
        ("other", "Other"),
    ], required=True, default="handbook")
    version = fields.Char(default="1.0")
    effective_date = fields.Date(default=fields.Date.today)
    document = fields.Binary(attachment=True, string="PDF document", required=True)
    document_filename = fields.Char()
    mandatory_for_all = fields.Boolean(default=True)
    mandatory_for_departments = fields.Many2many("hr.department")
    summary = fields.Text(translate=True)
    summary_ar = fields.Text(string="Summary (Arabic)")
    active = fields.Boolean(default=True)


class PolicyAcknowledgement(models.Model):
    _name = "mn.hr.policy.acknowledgement"
    _description = "Policy Acknowledgement"
    _order = "acknowledged_on desc"

    policy_id = fields.Many2one("mn.hr.policy", required=True, ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", required=True)
    acknowledged_on = fields.Datetime(default=fields.Datetime.now, required=True)
    version = fields.Char()
    signed_via = fields.Selection([
        ("portal", "Portal"), ("email", "Email"),
        ("paper", "Paper"), ("system", "System auto-attest"),
    ], default="portal")
    ip_address = fields.Char()
    notes = fields.Char()
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)
