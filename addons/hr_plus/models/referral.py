# -*- coding: utf-8 -*-
from odoo import fields, models


class Referral(models.Model):
    _name = "mn.hr.referral"
    _description = "Employee Referral"
    _inherit = ["mail.thread"]
    _order = "referral_date desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.referral") or "/",
        readonly=True, copy=False)
    referrer_id = fields.Many2one("hr.employee", required=True,
        string="Referred by", tracking=True)
    candidate_name = fields.Char(required=True, tracking=True)
    candidate_email = fields.Char()
    candidate_phone = fields.Char()
    candidate_linkedin = fields.Char()
    candidate_cv = fields.Binary(attachment=True)
    job_position = fields.Char()
    job_id = fields.Many2one("hr.job", string="Job opening")
    referral_date = fields.Date(default=fields.Date.today, required=True)
    bonus_amount = fields.Monetary(currency_field="currency_id")
    bonus_paid = fields.Boolean(default=False, tracking=True)
    bonus_paid_on = fields.Date()
    state = fields.Selection([
        ("new", "New"), ("screening", "Screening"),
        ("interview", "Interview"), ("offered", "Offered"),
        ("hired", "Hired"), ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ], default="new", tracking=True)
    hired_employee_id = fields.Many2one("hr.employee", tracking=True)
    hired_on = fields.Date()
    notes = fields.Text()
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="referrer_id.company_id", store=True)

    def action_hired(self):
        self.write({"state": "hired", "hired_on": fields.Date.today()})
    def action_pay_bonus(self):
        self.write({"bonus_paid": True, "bonus_paid_on": fields.Date.today()})
