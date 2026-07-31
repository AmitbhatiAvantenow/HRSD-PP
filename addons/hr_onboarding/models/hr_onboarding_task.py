from odoo import fields, models


class HrOnboardingTask(models.Model):
    _name = 'hr.onboarding.task'
    _description = 'Onboarding Task'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    onboarding_id = fields.Many2one('hr.onboarding', required=True, ondelete='cascade', index=True)
    stage_id = fields.Many2one(
        'hr.onboarding.stage', string='Journey Stage',
        help='Stage of the journey timeline this task belongs to.')
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    due_date = fields.Date()
    done = fields.Boolean(string='Done')
