from odoo import fields, models


class HrOnboardingStageLog(models.Model):
    _name = 'hr.onboarding.stage.log'
    _description = 'Onboarding Stage History'
    _order = 'date_entered'

    onboarding_id = fields.Many2one('hr.onboarding', required=True, ondelete='cascade', index=True)
    stage_id = fields.Many2one('hr.onboarding.stage', required=True, ondelete='cascade')
    date_entered = fields.Datetime(default=fields.Datetime.now, required=True)
