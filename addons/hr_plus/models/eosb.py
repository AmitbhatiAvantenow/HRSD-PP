# -*- coding: utf-8 -*-
"""End-of-Service Benefits (EOSB) — Gulf gratuity calculator.

Saudi labor law: half-month per year for first 5 years, full month per year thereafter.
UAE labor law: 21 days per year for first 5 years, 30 days thereafter.
Cap: total cannot exceed 2 years of salary."""
from odoo import api, fields, models, _


class EOSB(models.Model):
    _name = "mn.hr.eosb"
    _description = "End-of-Service Benefits"
    _inherit = ["mail.thread"]
    _order = "calc_date desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.eosb") or "/",
        readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    calc_date = fields.Date(default=fields.Date.today, required=True, tracking=True)
    country_law = fields.Selection([
        ("saudi", "Saudi Arabia"),
        ("uae", "United Arab Emirates"),
        ("kuwait", "Kuwait"),
        ("bahrain", "Bahrain"),
        ("qatar", "Qatar"),
        ("oman", "Oman"),
        ("custom", "Custom formula"),
    ], default="saudi", required=True, tracking=True)
    reason = fields.Selection([
        ("resignation", "Resignation"), ("termination", "Termination by employer"),
        ("retirement", "Retirement"), ("contract_end", "Contract end"),
        ("death", "Death"),
    ], default="resignation", tracking=True)
    employment_start = fields.Date(required=True, tracking=True)
    employment_end = fields.Date(required=True, default=fields.Date.today, tracking=True)
    last_basic_salary = fields.Monetary(currency_field="currency_id", required=True, tracking=True)
    allowances = fields.Monetary(currency_field="currency_id",
        help="Housing + transport + other allowances counted in EOSB base.")

    years_of_service = fields.Float(compute="_compute_calc", store=True)
    eosb_amount = fields.Monetary(currency_field="currency_id",
        compute="_compute_calc", store=True)
    breakdown = fields.Text(compute="_compute_calc", store=True)

    state = fields.Selection([
        ("draft", "Draft"), ("computed", "Computed"),
        ("approved", "Approved"), ("paid", "Paid"),
    ], default="draft", tracking=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    @api.depends("employment_start", "employment_end", "last_basic_salary",
                  "allowances", "country_law", "reason")
    def _compute_calc(self):
        for r in self:
            if not (r.employment_start and r.employment_end and r.last_basic_salary):
                r.years_of_service = 0; r.eosb_amount = 0; r.breakdown = ""
                continue
            days = (r.employment_end - r.employment_start).days
            years = days / 365.25
            r.years_of_service = round(years, 2)
            base = r.last_basic_salary + (r.allowances or 0)
            if r.country_law == "saudi":
                # Half month per year first 5 years, full month thereafter
                if years <= 5:
                    eosb = (base / 2) * years
                else:
                    eosb = (base / 2) * 5 + base * (years - 5)
                # Resignation penalties (Saudi Article 85)
                if r.reason == "resignation":
                    if years < 2: eosb = 0
                    elif years < 5: eosb *= 1.0 / 3.0
                    elif years < 10: eosb *= 2.0 / 3.0
                # Cap at 2 years salary
                eosb = min(eosb, base * 24)
                r.breakdown = (f"Saudi Article 84: half-month/year for first 5,"
                               f" full month/year thereafter. Years={years:.2f}, base={base},"
                               f" reason={r.reason}.")
            elif r.country_law == "uae":
                if years < 1: eosb = 0
                elif years <= 5: eosb = (base / 30) * 21 * years
                else: eosb = (base / 30) * 21 * 5 + (base / 30) * 30 * (years - 5)
                eosb = min(eosb, base * 24)
                r.breakdown = (f"UAE: 21 days/year first 5, 30 days/year thereafter."
                               f" Years={years:.2f}, base={base}.")
            else:
                eosb = (base / 2) * min(years, 5) + base * max(0, years - 5)
                r.breakdown = f"Generic Gulf formula. Years={years:.2f}, base={base}."
            r.eosb_amount = round(eosb, 2)

    def action_approve(self):
        self.write({"state": "approved"})
    def action_pay(self):
        self.write({"state": "paid"})
