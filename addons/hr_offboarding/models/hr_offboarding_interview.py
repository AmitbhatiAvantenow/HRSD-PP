from odoo import fields, models


class HrOffboardingInterview(models.Model):
    _name = 'hr.offboarding.interview'
    _description = 'Offboarding Exit Interview'
    _order = 'id desc'

    request_id = fields.Many2one('hr.offboarding.request', required=True, ondelete='cascade', index=True)
    scheduled_date = fields.Datetime(string='Scheduled On')
    interviewer_id = fields.Many2one('res.users', string='Interviewer')
    anonymous = fields.Boolean(string='Anonymous Mode')

    exit_reason = fields.Selection([
        ('better_opportunity', 'Better Opportunity'),
        ('compensation', 'Compensation'),
        ('relocation', 'Relocation'),
        ('higher_education', 'Higher Education'),
        ('health', 'Health / Personal'),
        ('management', 'Management / Culture'),
        ('performance', 'Performance / Involuntary'),
        ('other', 'Other'),
    ], string='Primary Reason')
    overall_rating = fields.Selection([
        ('1', '1 - Very Dissatisfied'),
        ('2', '2 - Dissatisfied'),
        ('3', '3 - Neutral'),
        ('4', '4 - Satisfied'),
        ('5', '5 - Very Satisfied'),
    ], string='Overall Experience')
    manager_feedback = fields.Text(string='Feedback about Manager')
    company_feedback = fields.Text(string='Feedback about Company')
    suggestions = fields.Text(string='Suggestions for Improvement')

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ], default='scheduled', required=True)
