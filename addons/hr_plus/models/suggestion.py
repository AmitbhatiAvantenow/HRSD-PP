# -*- coding: utf-8 -*-
from odoo import fields, models


class Suggestion(models.Model):
    _name = "mn.hr.suggestion"
    _description = "Suggestion Box"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.suggestion") or "/",
        readonly=True, copy=False)
    title = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one("hr.employee", tracking=True,
        help="Leave empty for anonymous.")
    is_anonymous = fields.Boolean(default=False, tracking=True)
    category = fields.Selection([
        ("process", "Process improvement"),
        ("benefit", "Benefits / perks"),
        ("workplace", "Workplace / facilities"),
        ("culture", "Culture"),
        ("tools", "Tools / systems"),
        ("safety", "Safety"),
        ("training", "Training"),
        ("other", "Other"),
    ], default="process", required=True)
    description = fields.Text(required=True)
    expected_benefit = fields.Text()
    estimated_savings = fields.Monetary(currency_field="currency_id")
    upvote_count = fields.Integer(default=0,
        help="How many employees upvoted this idea.")
    state = fields.Selection([
        ("new", "New"), ("reviewing", "Under review"),
        ("accepted", "Accepted"), ("rejected", "Rejected"),
        ("implemented", "Implemented"),
    ], default="new", tracking=True)
    reviewed_by_id = fields.Many2one("res.users", tracking=True)
    review_comments = fields.Text()
    implemented_on = fields.Date()
    reward_amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        default=lambda s: s.env.company)
