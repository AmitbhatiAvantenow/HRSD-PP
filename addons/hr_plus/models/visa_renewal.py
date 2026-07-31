# -*- coding: utf-8 -*-
from odoo import api, fields, models


class VisaRenewal(models.Model):
    _name = "mn.hr.visa.renewal"
    _description = "Visa / Iqama Renewal Workflow"
    _inherit = ["mail.thread"]
    _order = "target_renewal_date asc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.visa.renewal") or "/",
        readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    renewal_type = fields.Selection([
        ("iqama", "Iqama renewal"),
        ("work_visa", "Work visa renewal"),
        ("residence", "Residence permit"),
        ("dependent_visa", "Dependent visa"),
        ("exit_reentry", "Exit/Re-entry permit"),
        ("other", "Other"),
    ], required=True, default="iqama", tracking=True)
    current_expiry = fields.Date(required=True, tracking=True)
    target_renewal_date = fields.Date(tracking=True,
        help="Date by which renewal must be completed.")
    days_remaining = fields.Integer(compute="_compute_days")

    state = fields.Selection([
        ("draft", "Draft"),
        ("docs_collection", "Collecting documents"),
        ("medical", "Medical exam"),
        ("submitted", "Submitted to Mol/MOI"),
        ("payment", "Awaiting payment"),
        ("processing", "Processing"),
        ("approved", "Approved"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    ], default="draft", tracking=True)
    new_expiry = fields.Date(tracking=True)
    fee_amount = fields.Monetary(currency_field="currency_id")
    paid_by = fields.Selection([
        ("company", "Company"), ("employee", "Employee"),
    ], default="company")

    assigned_to_id = fields.Many2one("res.users", tracking=True)
    notes = fields.Text()
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    def _compute_days(self):
        today = fields.Date.today()
        for r in self:
            r.days_remaining = (r.current_expiry - today).days if r.current_expiry else 0
