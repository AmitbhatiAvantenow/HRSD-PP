# -*- coding: utf-8 -*-
"""mn.hr.document.tracker — track passport / Iqama / visa / licence
expiry with cron alerts at 90 / 60 / 30 / 14 / 7 days before."""
from datetime import timedelta
from odoo import api, fields, models, _


class DocumentType(models.Model):
    _name = "mn.hr.document.type"
    _description = "HR Document Type"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    name_ar = fields.Char(string="Name (Arabic)")
    code = fields.Char()
    icon = fields.Char(default="fa-id-card")
    notice_days = fields.Char(default="90,60,30,14,7",
        help="Comma-separated days-before-expiry to fire alerts.")
    active = fields.Boolean(default=True)


class DocumentTracker(models.Model):
    _name = "mn.hr.document.tracker"
    _description = "Employee Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "expiry_date asc"

    employee_id = fields.Many2one("hr.employee", required=True,
        ondelete="cascade", tracking=True)
    document_type_id = fields.Many2one("mn.hr.document.type", required=True, tracking=True)
    document_number = fields.Char(string="Document #", tracking=True)
    issue_date = fields.Date(tracking=True)
    expiry_date = fields.Date(tracking=True, required=True)
    country_id = fields.Many2one("res.country", string="Issuing country")
    notes = fields.Text()
    document_file = fields.Binary(attachment=True)
    document_filename = fields.Char()

    days_to_expiry = fields.Integer(compute="_compute_days", store=True)
    state = fields.Selection([
        ("valid", "Valid"),
        ("warning", "Expiring soon"),
        ("critical", "Expires < 30 days"),
        ("expired", "Expired"),
    ], compute="_compute_state", store=True, default="valid")
    last_alert_sent = fields.Datetime(readonly=True)
    last_alert_days = fields.Integer(readonly=True)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    @api.depends("expiry_date")
    def _compute_days(self):
        today = fields.Date.today()
        for r in self:
            r.days_to_expiry = (r.expiry_date - today).days if r.expiry_date else 0

    @api.depends("days_to_expiry")
    def _compute_state(self):
        for r in self:
            if r.days_to_expiry < 0: r.state = "expired"
            elif r.days_to_expiry < 30: r.state = "critical"
            elif r.days_to_expiry < 90: r.state = "warning"
            else: r.state = "valid"

    @api.model
    def _cron_check_expiries(self):
        """Fire activity + chatter message for each document hitting a notice threshold."""
        today = fields.Date.today()
        for r in self.search([("expiry_date", ">=", today - timedelta(days=1))]):
            try:
                thresholds = [int(d.strip()) for d in (r.document_type_id.notice_days or "").split(",") if d.strip()]
            except Exception:
                thresholds = [90, 60, 30, 14, 7]
            for t in sorted(thresholds, reverse=True):
                if r.days_to_expiry == t and r.last_alert_days != t:
                    r.message_post(body=_(
                        "%s for %s expires in %d days (on %s).") % (
                        r.document_type_id.name, r.employee_id.name,
                        t, r.expiry_date))
                    if r.employee_id.parent_id and r.employee_id.parent_id.user_id:
                        r.activity_schedule(
                            "mail.mail_activity_data_warning",
                            user_id=r.employee_id.parent_id.user_id.id,
                            summary=_("Renew %s for %s") % (
                                r.document_type_id.name, r.employee_id.name))
                    r.last_alert_sent = fields.Datetime.now()
                    r.last_alert_days = t
                    break
