# -*- coding: utf-8 -*-
"""Training + certification tracking with expiry alerts."""
from datetime import timedelta
from odoo import api, fields, models, _


class Training(models.Model):
    _name = "mn.hr.training"
    _description = "Training / Course"
    _inherit = ["mail.thread"]
    _order = "completion_date desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.training") or "/",
        readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    title = fields.Char(required=True, tracking=True)
    provider = fields.Char()
    category = fields.Selection([
        ("technical", "Technical"),
        ("soft_skills", "Soft skills"),
        ("compliance", "Compliance / regulatory"),
        ("safety", "Safety"),
        ("leadership", "Leadership"),
        ("language", "Language"),
        ("other", "Other"),
    ], default="technical", tracking=True)
    delivery = fields.Selection([
        ("classroom", "Classroom"), ("online", "Online"),
        ("workshop", "Workshop"), ("conference", "Conference"),
        ("self_study", "Self-study"),
    ], default="online")
    is_mandatory = fields.Boolean(default=False)
    is_certified = fields.Boolean(default=False)
    start_date = fields.Date()
    completion_date = fields.Date()
    duration_hours = fields.Float()
    cost = fields.Monetary(currency_field="currency_id")
    paid_by = fields.Selection([
        ("company", "Company"), ("employee", "Employee"),
        ("shared", "Shared"),
    ], default="company")
    score = fields.Float(help="Final score 0-100.")
    certificate_no = fields.Char()
    certificate_expiry = fields.Date(tracking=True)
    days_to_expiry = fields.Integer(compute="_compute_days")
    certificate_file = fields.Binary(attachment=True)
    state = fields.Selection([
        ("planned", "Planned"), ("ongoing", "Ongoing"),
        ("completed", "Completed"), ("failed", "Failed"),
        ("expired", "Expired"),
    ], default="planned", tracking=True, compute="_compute_state", store=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    @api.depends("certificate_expiry")
    def _compute_days(self):
        today = fields.Date.today()
        for r in self:
            r.days_to_expiry = (r.certificate_expiry - today).days if r.certificate_expiry else 0

    @api.depends("completion_date", "certificate_expiry")
    def _compute_state(self):
        today = fields.Date.today()
        for r in self:
            if r.certificate_expiry and r.certificate_expiry < today:
                r.state = "expired"
            elif r.completion_date:
                r.state = "completed"
            elif r.start_date and r.start_date <= today:
                r.state = "ongoing"

    @api.model
    def _cron_cert_expiry(self):
        soon = fields.Date.today() + timedelta(days=30)
        for r in self.search([("certificate_expiry", "<=", soon),
                                ("state", "=", "completed")]):
            r.message_post(body=_(
                "Certification '%s' for %s expires on %s.") % (
                r.title, r.employee_id.name, r.certificate_expiry))
