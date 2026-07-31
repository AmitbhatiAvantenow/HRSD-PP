from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)


class HrResumeJob(models.Model):
    _name = 'hr.resume.job'
    _description = 'Resume Screening Job Profile'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Job Title', required=True)
    required_skills = fields.Text(
        string='Required Skills',
        help='Comma-separated skills: Python, SQL, Leadership, ...'
    )
    preferred_skills = fields.Text(
        string='Preferred / Bonus Skills',
        help='Nice-to-have skills (comma-separated)'
    )
    min_experience = fields.Integer(string='Minimum Experience (Years)', default=0)
    education_level = fields.Selection([
        ('any',         'Any Level'),
        ('high_school', 'High School / Diploma'),
        ('bachelor',    "Bachelor's Degree"),
        ('master',      "Master's Degree"),
        ('phd',         'PhD / Doctorate'),
    ], string='Minimum Education', default='bachelor')
    job_description = fields.Text(string='Job Description / Requirements')
    candidate_ids = fields.One2many('hr.resume.candidate', 'job_id', string='Candidates')
    candidate_count = fields.Integer(compute='_compute_counts', string='Candidate Count')
    top_score = fields.Float(compute='_compute_counts', string='Top Score (%)', digits=(5, 1))
    created_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)

    def action_view_candidates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Candidates — {self.name}',
            'res_model': 'hr.resume.candidate',
            'view_mode': 'list,form',
            'domain': [('job_id', '=', self.id)],
            'context': {'default_job_id': self.id},
        }

    @api.depends('candidate_ids', 'candidate_ids.score_overall')
    def _compute_counts(self):
        for rec in self:
            candidates = rec.candidate_ids
            rec.candidate_count = len(candidates)
            scores = candidates.mapped('score_overall')
            rec.top_score = max(scores) if scores else 0.0


class HrResumeCandidate(models.Model):
    _name = 'hr.resume.candidate'
    _description = 'Resume Screening Candidate'
    _order = 'score_overall desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Candidate Name', default='Unknown Candidate')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    job_id = fields.Many2one(
        'hr.resume.job', string='Job Profile',
        required=True, ondelete='cascade', index=True
    )
    employee_id = fields.Many2one('hr.employee', string='Linked Employee', ondelete='set null')
    file_data = fields.Binary(string='Resume File', attachment=True)
    file_name = fields.Char(string='File Name')
    file_size_kb = fields.Integer(string='File Size (KB)')
    raw_text = fields.Text(string='Extracted Resume Text')
    detected_skills = fields.Text(string='Detected Skills (JSON)')
    experience_years = fields.Float(string='Experience (Years)', digits=(4, 1))
    education_level = fields.Selection([
        ('high_school', 'High School / Diploma'),
        ('bachelor',    "Bachelor's Degree"),
        ('master',      "Master's Degree"),
        ('phd',         'PhD / Doctorate'),
    ], string='Education Level')
    score_overall = fields.Float(string='Overall Score (%)', digits=(5, 1))
    score_skills = fields.Float(string='Skills Score (%)', digits=(5, 1))
    score_experience = fields.Float(string='Experience Score (%)', digits=(5, 1))
    score_education = fields.Float(string='Education Score (%)', digits=(5, 1))
    score_content = fields.Float(string='Content Match (%)', digits=(5, 1))
    rank = fields.Integer(string='Rank', default=0)
    state = fields.Selection([
        ('uploaded',  'Uploaded'),
        ('parsed',    'Parsed'),
        ('scored',    'Scored'),
        ('shortlisted', 'Shortlisted'),
        ('rejected',  'Rejected'),
    ], default='uploaded', string='Status', required=True)
    notes = fields.Text(string='HR Notes')
    uploaded_by = fields.Many2one(
        'res.users', string='Uploaded By',
        default=lambda self: self.env.user, readonly=True
    )

    def get_skills_list(self):
        try:
            return json.loads(self.detected_skills or '[]')
        except Exception:
            return []

    def action_shortlist(self):
        self.write({'state': 'shortlisted'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_link_employee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'list,form',
            'target': 'new',
        }
