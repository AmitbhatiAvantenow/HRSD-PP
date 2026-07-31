from odoo import models, fields


class HrRecruitmentNote(models.Model):
    _name = 'hr.recruitment.note'
    _description = 'Recruitment Work Note'
    _order = 'create_date desc'
    _rec_name = 'requirement_id'

    requirement_id = fields.Many2one('hr.recruitment', string='Requirement', required=True, ondelete='cascade', index=True)
    author_id = fields.Many2one('res.users', string='Author', default=lambda self: self.env.user, required=True)
    body = fields.Text(string='Comment', required=True)
