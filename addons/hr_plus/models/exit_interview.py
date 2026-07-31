# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ExitInterview(models.Model):
    _name = "mn.hr.exit.interview"
    _description = "Exit Interview"
    _inherit = ["mail.thread"]
    _order = "interview_date desc"

    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    interview_date = fields.Date(default=fields.Date.today, required=True, tracking=True)
    interviewer_id = fields.Many2one("res.users", default=lambda s: s.env.user)
    last_day = fields.Date()
    leaving_reason = fields.Selection([
        ("career_growth", "Better career opportunity"),
        ("compensation", "Better compensation"),
        ("relocation", "Relocation"),
        ("family", "Family reasons"),
        ("workload", "Workload / burnout"),
        ("management", "Management issues"),
        ("culture", "Company culture"),
        ("personal", "Personal"),
        ("end_of_contract", "End of contract"),
        ("other", "Other"),
    ], required=True, default="career_growth", tracking=True)

    # Structured ratings
    work_satisfaction = fields.Selection([
        ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"),
    ], string="Work satisfaction")
    management_rating = fields.Selection([
        ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"),
    ])
    compensation_rating = fields.Selection([
        ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"),
    ])
    culture_rating = fields.Selection([
        ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"),
    ])
    recommend_score = fields.Integer(string="NPS (0-10)",
        help="Would recommend the company as an employer?")

    what_went_well = fields.Text()
    what_could_improve = fields.Text()
    suggestions = fields.Text()
    rehire_eligible = fields.Boolean(default=True)
    notes = fields.Text()

    state = fields.Selection([
        ("draft", "Draft"), ("done", "Completed"), ("archived", "Archived"),
    ], default="draft", tracking=True)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)
