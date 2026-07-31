from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrAppraisalGoal(models.Model):
    _name = 'hr.appraisal.goal'
    _description = 'Appraisal Goal / OKR'
    _order = 'sequence, id'

    appraisal_id = fields.Many2one('hr.appraisal', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Goal', required=True)
    description = fields.Text()
    category = fields.Selection([
        ('business', 'Business Objective'),
        ('development', 'Development Goal'),
        ('behavioral', 'Behavioral / Values'),
    ], default='business', required=True)
    weight = fields.Integer(string='Weight (%)', default=20)
    target_value = fields.Char(string='Target / KPI')
    self_progress = fields.Integer(string='Self Progress (%)', default=0)
    manager_progress = fields.Integer(string='Manager Progress (%)', default=0)
    status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('achieved', 'Achieved'),
        ('partially_achieved', 'Partially Achieved'),
        ('not_achieved', 'Not Achieved'),
    ], default='not_started')

    @api.constrains('weight')
    def _check_weight(self):
        for rec in self:
            if not (0 <= rec.weight <= 100):
                raise ValidationError('Goal weight must be between 0 and 100.')

    @api.constrains('self_progress', 'manager_progress')
    def _check_progress(self):
        for rec in self:
            if not (0 <= rec.self_progress <= 100):
                raise ValidationError('Self progress must be between 0 and 100.')
            if not (0 <= rec.manager_progress <= 100):
                raise ValidationError('Manager progress must be between 0 and 100.')


class HrAppraisalCompetency(models.Model):
    _name = 'hr.appraisal.competency'
    _description = 'Appraisal Competency Rating'
    _order = 'sequence, id'

    appraisal_id = fields.Many2one('hr.appraisal', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Selection([
        ('communication', 'Communication'),
        ('teamwork', 'Teamwork & Collaboration'),
        ('problem_solving', 'Problem Solving'),
        ('leadership', 'Leadership'),
        ('technical_skills', 'Technical / Job Skills'),
        ('adaptability', 'Adaptability'),
        ('ownership', 'Ownership & Accountability'),
        ('quality', 'Quality of Work'),
    ], required=True, default='communication')
    self_score = fields.Integer(string='Self Rating (1-5)', default=3)
    manager_score = fields.Integer(string='Manager Rating (1-5)', default=3)
    self_comments = fields.Text()
    manager_comments = fields.Text()

    @api.constrains('self_score', 'manager_score')
    def _check_scores(self):
        for rec in self:
            if not (1 <= rec.self_score <= 5):
                raise ValidationError('Self rating must be between 1 and 5.')
            if not (1 <= rec.manager_score <= 5):
                raise ValidationError('Manager rating must be between 1 and 5.')


class HrAppraisalFeedback(models.Model):
    _name = 'hr.appraisal.feedback'
    _description = 'Appraisal 360° Feedback'
    _order = 'id desc'

    appraisal_id = fields.Many2one('hr.appraisal', required=True, ondelete='cascade', index=True)
    reviewer_id = fields.Many2one('hr.employee', string='Reviewer')
    relation = fields.Selection([
        ('self', 'Self'),
        ('manager', 'Manager'),
        ('peer', 'Peer'),
        ('subordinate', 'Direct Report'),
        ('other', 'Other / Stakeholder'),
    ], default='peer', required=True)
    rating = fields.Integer(string='Overall Rating (1-5)', default=3)
    comments = fields.Text()
    submitted_date = fields.Datetime(default=fields.Datetime.now)

    @api.constrains('rating')
    def _check_rating(self):
        for rec in self:
            if not (1 <= rec.rating <= 5):
                raise ValidationError('Feedback rating must be between 1 and 5.')
