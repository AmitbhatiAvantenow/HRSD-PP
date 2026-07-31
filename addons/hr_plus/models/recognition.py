# -*- coding: utf-8 -*-
from odoo import fields, models


class Recognition(models.Model):
    _name = "mn.hr.recognition"
    _description = "Employee Recognition / Award"
    _inherit = ["mail.thread"]
    _order = "award_date desc"

    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    nominated_by_id = fields.Many2one("res.users", default=lambda s: s.env.user)
    award_date = fields.Date(default=fields.Date.today, required=True, tracking=True)
    award_type = fields.Selection([
        ("employee_of_month", "Employee of the Month"),
        ("employee_of_year", "Employee of the Year"),
        ("kudos", "Kudos / Peer recognition"),
        ("milestone", "Service milestone (5/10/15 years)"),
        ("performance", "Performance bonus"),
        ("innovation", "Innovation award"),
        ("teamwork", "Teamwork award"),
        ("customer_service", "Customer service excellence"),
        ("safety", "Safety champion"),
        ("other", "Other"),
    ], required=True, default="kudos", tracking=True)
    category = fields.Selection([
        ("monthly", "Monthly"), ("quarterly", "Quarterly"),
        ("annual", "Annual"), ("spot", "Spot award"),
    ], default="spot")
    citation = fields.Text(string="Reason / citation",
        help="Why is this person being recognised?")
    award_value = fields.Monetary(currency_field="currency_id",
        help="Cash component (if any).")
    public = fields.Boolean(default=True,
        help="Announce on the company wall.")
    photo = fields.Binary(attachment=True)
    state = fields.Selection([
        ("draft", "Draft"), ("approved", "Approved"),
        ("announced", "Announced"), ("paid", "Paid"),
    ], default="draft", tracking=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    def action_announce(self):
        for r in self:
            r.message_post(body=f"🏆 <strong>{r.employee_id.name}</strong> has been recognised: <em>{r.name}</em>. {r.citation or ''}")
            r.state = "announced"
