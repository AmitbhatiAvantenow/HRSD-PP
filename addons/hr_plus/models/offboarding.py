# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OffboardingChecklist(models.Model):
    _name = "mn.hr.offboarding.checklist"
    _description = "Employee Offboarding Checklist"
    _inherit = ["mail.thread"]
    _order = "last_day desc"

    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    last_day = fields.Date(required=True)
    reason = fields.Selection([
        ("resignation", "Resignation"), ("termination", "Termination"),
        ("retirement", "Retirement"), ("contract_end", "Contract end"),
        ("other", "Other"),
    ], default="resignation")
    exit_interview_done = fields.Boolean()
    exit_interview_notes = fields.Text()
    assets_returned = fields.Boolean()
    final_settlement_paid = fields.Boolean()
    eosb_paid = fields.Monetary(currency_field="currency_id",
        help="End-of-service benefits paid.")
    knowledge_handover_done = fields.Boolean()
    system_access_revoked = fields.Boolean()
    rehire_eligible = fields.Boolean(default=True)
    state = fields.Selection([
        ("in_progress", "In progress"), ("done", "Completed"),
    ], default="in_progress", tracking=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)
