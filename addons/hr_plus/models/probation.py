# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models, _


class Probation(models.Model):
    _name = "mn.hr.probation"
    _description = "Probation Period"
    _inherit = ["mail.thread"]
    _order = "end_date asc"

    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date(required=True, tracking=True)
    duration_months = fields.Integer(default=3)
    extended_to = fields.Date(tracking=True)
    days_remaining = fields.Integer(compute="_compute_days_remaining")
    review_outcome = fields.Selection([
        ("pass", "Confirmed"),
        ("extend", "Extended"),
        ("fail", "Failed / terminated"),
    ], tracking=True)
    review_notes = fields.Text()
    reviewed_by_id = fields.Many2one("res.users", tracking=True)
    reviewed_on = fields.Date()
    state = fields.Selection([
        ("active", "Active"), ("review_due", "Review due"),
        ("confirmed", "Confirmed"), ("extended", "Extended"),
        ("failed", "Failed"),
    ], default="active", compute="_compute_state", store=True, tracking=True)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    def _compute_days_remaining(self):
        today = fields.Date.today()
        for r in self:
            target = r.extended_to or r.end_date
            r.days_remaining = (target - today).days if target else 0

    @api.depends("review_outcome", "end_date", "extended_to")
    def _compute_state(self):
        today = fields.Date.today()
        for r in self:
            if r.review_outcome == "pass": r.state = "confirmed"
            elif r.review_outcome == "extend": r.state = "extended"
            elif r.review_outcome == "fail": r.state = "failed"
            else:
                target = r.extended_to or r.end_date
                if target and target <= today + timedelta(days=14):
                    r.state = "review_due"
                else: r.state = "active"

    @api.model
    def _cron_alert_due(self):
        """Notify manager 14/7/1 day before probation ends."""
        Activity = self.env["mail.activity"]
        today = fields.Date.today()
        for r in self.search([("state", "in", ("active", "review_due"))]):
            target = r.extended_to or r.end_date
            if not target: continue
            days = (target - today).days
            if days in (14, 7, 1):
                if r.employee_id.parent_id and r.employee_id.parent_id.user_id:
                    r.activity_schedule(
                        "mail.mail_activity_data_warning",
                        user_id=r.employee_id.parent_id.user_id.id,
                        summary=_("Probation review due — %s") % r.employee_id.name)
                r.message_post(body=_("Probation review due in %d days.") % days)
