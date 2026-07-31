# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OnboardingTemplate(models.Model):
    _name = "mn.hr.onboarding.template"
    _description = "Onboarding Task Template"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    department = fields.Selection([
        ("hr", "HR"), ("it", "IT"), ("finance", "Finance"),
        ("manager", "Direct manager"), ("admin", "Admin / facilities"),
    ], default="hr")
    days_after_start = fields.Integer(default=0)
    description = fields.Text()
    active = fields.Boolean(default=True)


class OnboardingChecklist(models.Model):
    _name = "mn.hr.onboarding.checklist"
    _description = "Employee Onboarding Checklist"
    _inherit = ["mail.thread"]
    _order = "start_date desc"

    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    start_date = fields.Date(required=True, default=fields.Date.today)
    target_complete_date = fields.Date()
    progress_pct = fields.Float(compute="_compute_progress", store=True)
    task_ids = fields.One2many("mn.hr.onboarding.task", "checklist_id")
    state = fields.Selection([
        ("in_progress", "In progress"),
        ("done", "Completed"),
        ("abandoned", "Abandoned"),
    ], default="in_progress", tracking=True)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    @api.depends("task_ids.state")
    def _compute_progress(self):
        for r in self:
            total = len(r.task_ids)
            done = len(r.task_ids.filtered(lambda t: t.state == "done"))
            r.progress_pct = (done / total * 100) if total else 0

    def action_generate_tasks(self):
        """Spawn one task per onboarding template."""
        Task = self.env["mn.hr.onboarding.task"].sudo()
        templates = self.env["mn.hr.onboarding.template"].search([("active", "=", True)])
        for r in self:
            r.task_ids.unlink()
            for t in templates:
                Task.create({
                    "checklist_id": r.id, "name": t.name,
                    "department": t.department,
                    "due_date": fields.Date.add(r.start_date, days=t.days_after_start),
                })


class OnboardingTask(models.Model):
    _name = "mn.hr.onboarding.task"
    _description = "Onboarding Task"
    _order = "due_date asc"

    checklist_id = fields.Many2one("mn.hr.onboarding.checklist", required=True,
        ondelete="cascade")
    employee_id = fields.Many2one("hr.employee",
        related="checklist_id.employee_id", store=True)
    name = fields.Char(required=True)
    department = fields.Selection([
        ("hr", "HR"), ("it", "IT"), ("finance", "Finance"),
        ("manager", "Direct manager"), ("admin", "Admin / facilities"),
    ], default="hr")
    due_date = fields.Date()
    assigned_user_id = fields.Many2one("res.users")
    state = fields.Selection([
        ("new", "New"), ("in_progress", "In progress"),
        ("done", "Done"), ("skipped", "Skipped"),
    ], default="new")
    completed_on = fields.Date()
    notes = fields.Text()

    def action_done(self):
        self.write({"state": "done", "completed_on": fields.Date.today()})
