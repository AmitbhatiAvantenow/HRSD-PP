# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BusinessTrip(models.Model):
    _name = "mn.hr.business.trip"
    _description = "Business Trip"
    _inherit = ["mail.thread"]
    _order = "start_date desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.business.trip") or "/",
        readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    destination_country_id = fields.Many2one("res.country", tracking=True)
    destination_city = fields.Char(tracking=True)
    start_date = fields.Date(required=True, tracking=True)
    end_date = fields.Date(required=True, tracking=True)
    duration_days = fields.Integer(compute="_compute_duration", store=True)
    purpose = fields.Text(required=True)
    accompanying_employees = fields.Many2many("hr.employee",
        "mn_hr_trip_employees_rel", "trip_id", "employee_id",
        string="Travelling with")

    advance_amount = fields.Monetary(currency_field="currency_id")
    per_diem_amount = fields.Monetary(currency_field="currency_id")
    reimbursement_amount = fields.Monetary(currency_field="currency_id")
    total_cost = fields.Monetary(compute="_compute_total", currency_field="currency_id")
    invoices_uploaded = fields.Boolean()

    state = fields.Selection([
        ("draft", "Draft"), ("submitted", "Submitted"),
        ("approved", "Approved"), ("rejected", "Rejected"),
        ("travelling", "Travelling"), ("returned", "Returned"),
        ("settled", "Settled"),
    ], default="draft", tracking=True)
    approver_id = fields.Many2one("res.users", tracking=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    @api.depends("start_date", "end_date")
    def _compute_duration(self):
        for r in self:
            r.duration_days = (r.end_date - r.start_date).days + 1 if (r.start_date and r.end_date) else 0

    @api.depends("advance_amount", "per_diem_amount", "reimbursement_amount")
    def _compute_total(self):
        for r in self:
            r.total_cost = (r.advance_amount or 0) + (r.per_diem_amount or 0) + (r.reimbursement_amount or 0)

    def action_submit(self): self.write({"state": "submitted"})
    def action_approve(self): self.write({"state": "approved", "approver_id": self.env.user.id})
    def action_reject(self): self.write({"state": "rejected"})
    def action_returned(self): self.write({"state": "returned"})
    def action_settle(self): self.write({"state": "settled"})
