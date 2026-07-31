from odoo import fields, models


class HrOffboardingStageLog(models.Model):
    _name = 'hr.offboarding.stage.log'
    _description = 'Offboarding Stage History'
    _order = 'date_entered'

    request_id = fields.Many2one('hr.offboarding.request', required=True, ondelete='cascade', index=True)
    stage_id = fields.Many2one('hr.offboarding.stage', required=True, ondelete='cascade')
    date_entered = fields.Datetime(default=fields.Datetime.now, required=True)
