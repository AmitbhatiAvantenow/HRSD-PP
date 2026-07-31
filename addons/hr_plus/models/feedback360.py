# -*- coding: utf-8 -*-
"""360-degree feedback with structured questionnaire."""
import secrets
from odoo import api, fields, models


class Feedback360(models.Model):
    _name = "mn.hr.feedback360"
    _description = "360-degree Feedback Cycle"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    name = fields.Char(required=True, tracking=True,
        default=lambda s: f"360 Review — {fields.Date.today()}")
    subject_id = fields.Many2one("hr.employee", required=True,
        string="Reviewed employee", tracking=True)
    cycle_year = fields.Integer(default=lambda s: fields.Date.today().year)
    cycle_quarter = fields.Selection([
        ("Q1", "Q1"), ("Q2", "Q2"), ("Q3", "Q3"), ("Q4", "Q4"),
    ], default="Q4")
    open_date = fields.Date(default=fields.Date.today)
    close_date = fields.Date()
    reviewer_ids = fields.Many2many("hr.employee",
        "mn_hr_360_reviewers_rel", "cycle_id", "reviewer_id",
        string="Reviewers")
    public_token = fields.Char(default=lambda s: secrets.token_urlsafe(16),
        readonly=True, copy=False)
    response_count = fields.Integer(compute="_compute_counts")
    target_count = fields.Integer(compute="_compute_counts")
    completion_pct = fields.Float(compute="_compute_counts")
    average_rating = fields.Float(compute="_compute_avg")
    state = fields.Selection([
        ("draft", "Draft"), ("open", "Open"),
        ("closed", "Closed"), ("shared", "Shared with employee"),
    ], default="draft", tracking=True)
    response_ids = fields.One2many("mn.hr.feedback360.response", "cycle_id")
    company_id = fields.Many2one("res.company",
        related="subject_id.company_id", store=True)

    def _compute_counts(self):
        for r in self:
            r.target_count = len(r.reviewer_ids)
            r.response_count = len(r.response_ids)
            r.completion_pct = (r.response_count / r.target_count * 100) if r.target_count else 0

    def _compute_avg(self):
        for r in self:
            ratings = []
            for resp in r.response_ids:
                for ar in resp.answer_ids:
                    if ar.rating: ratings.append(int(ar.rating))
            r.average_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0


class Feedback360Question(models.Model):
    _name = "mn.hr.feedback360.question"
    _description = "360 feedback question template"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    competency = fields.Selection([
        ("communication", "Communication"),
        ("teamwork", "Teamwork"),
        ("leadership", "Leadership"),
        ("quality", "Quality of work"),
        ("ownership", "Ownership"),
        ("integrity", "Integrity"),
        ("initiative", "Initiative"),
        ("technical", "Technical skill"),
    ], default="communication")
    question_type = fields.Selection([
        ("rating", "Rating 1-5"),
        ("text", "Free text"),
    ], default="rating", required=True)
    active = fields.Boolean(default=True)


class Feedback360Response(models.Model):
    _name = "mn.hr.feedback360.response"
    _description = "360 feedback response"
    _order = "submit_date desc"

    cycle_id = fields.Many2one("mn.hr.feedback360", required=True, ondelete="cascade")
    reviewer_id = fields.Many2one("hr.employee", required=True)
    is_anonymous = fields.Boolean(default=False)
    submit_date = fields.Datetime(default=fields.Datetime.now)
    overall_comment = fields.Text()
    answer_ids = fields.One2many("mn.hr.feedback360.answer", "response_id")


class Feedback360Answer(models.Model):
    _name = "mn.hr.feedback360.answer"
    _description = "Per-question answer"

    response_id = fields.Many2one("mn.hr.feedback360.response", required=True, ondelete="cascade")
    question_id = fields.Many2one("mn.hr.feedback360.question", required=True)
    rating = fields.Selection([
        ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"),
    ])
    text = fields.Text()
