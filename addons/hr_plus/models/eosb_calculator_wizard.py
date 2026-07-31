# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EOSBCalculatorWizard(models.TransientModel):
    _name = "mn.hr.eosb.calculator.wizard"
    _description = "EOSB Calculator Wizard"

    employee_id = fields.Many2one("hr.employee", required=True)
    country_law = fields.Selection([
        ("saudi", "Saudi Arabia"), ("uae", "UAE"),
        ("kuwait", "Kuwait"), ("bahrain", "Bahrain"),
        ("qatar", "Qatar"), ("oman", "Oman"),
    ], default="saudi", required=True)
    reason = fields.Selection([
        ("resignation", "Resignation"),
        ("termination", "Termination by employer"),
        ("retirement", "Retirement"),
        ("contract_end", "Contract end"),
    ], default="resignation", required=True)
    employment_start = fields.Date(required=True)
    employment_end = fields.Date(required=True, default=fields.Date.today)
    last_basic_salary = fields.Monetary(currency_field="currency_id", required=True)
    allowances = fields.Monetary(currency_field="currency_id")
    eosb_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    years_of_service = fields.Float(readonly=True)
    breakdown = fields.Text(readonly=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)

    def action_calculate(self):
        self.ensure_one()
        # Reuse the EOSB model's logic by creating a transient record
        e = self.env["mn.hr.eosb"].new({
            "employee_id": self.employee_id.id,
            "country_law": self.country_law,
            "reason": self.reason,
            "employment_start": self.employment_start,
            "employment_end": self.employment_end,
            "last_basic_salary": self.last_basic_salary,
            "allowances": self.allowances,
        })
        e._compute_calc()
        self.eosb_amount = e.eosb_amount
        self.years_of_service = e.years_of_service
        self.breakdown = e.breakdown
        return {"type": "ir.actions.act_window",
                "res_model": "mn.hr.eosb.calculator.wizard",
                "view_mode": "form", "res_id": self.id, "target": "new"}

    def action_save_as_record(self):
        self.ensure_one()
        rec = self.env["mn.hr.eosb"].create({
            "employee_id": self.employee_id.id,
            "country_law": self.country_law, "reason": self.reason,
            "employment_start": self.employment_start,
            "employment_end": self.employment_end,
            "last_basic_salary": self.last_basic_salary,
            "allowances": self.allowances,
        })
        return {"type": "ir.actions.act_window",
                "res_model": "mn.hr.eosb",
                "view_mode": "form", "res_id": rec.id}
