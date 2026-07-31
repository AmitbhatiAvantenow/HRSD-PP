import json
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class HrInterviewSession(models.Model):
    _name = 'hr.interview.session'
    _description = 'Interview Question Session'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Session Name', required=True)
    job_title = fields.Char(string='Job Title', required=True)
    industry = fields.Char(string='Industry')
    experience_level = fields.Selection([
        ('junior',    'Junior (0–2 yrs)'),
        ('mid',       'Mid-Level (3–5 yrs)'),
        ('senior',    'Senior (6–10 yrs)'),
        ('executive', 'Executive (10+ yrs)'),
    ], string='Experience Level', default='mid')
    question_count = fields.Integer(string='Questions Generated', default=0)
    competencies = fields.Char(string='Competencies (JSON array)')
    question_types = fields.Char(string='Question Types (JSON array)')
    company_context = fields.Text(string='Company / Role Context')
    questions_json = fields.Text(string='Generated Questions (JSON)')
    created_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True, string='Created By')

    @api.depends('questions_json')
    def _compute_question_count(self):
        for rec in self:
            try:
                qs = json.loads(rec.questions_json or '[]')
                rec.question_count = len(qs)
            except Exception:
                rec.question_count = 0

    def get_questions(self):
        self.ensure_one()
        try:
            return json.loads(self.questions_json or '[]')
        except Exception:
            return []

    def session_summary(self):
        self.ensure_one()
        try:
            types = json.loads(self.question_types or '[]')
            competencies = json.loads(self.competencies or '[]')
        except Exception:
            types, competencies = [], []
        return {
            'id': self.id,
            'name': self.name,
            'job_title': self.job_title,
            'industry': self.industry or '',
            'experience_level': self.experience_level,
            'question_count': self.question_count,
            'competencies': competencies,
            'question_types': types,
            'created_by': self.created_by.name or '',
            'create_date': self.create_date.strftime('%d %b %Y, %H:%M') if self.create_date else '',
        }
