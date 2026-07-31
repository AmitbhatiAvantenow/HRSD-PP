from odoo import models, fields, api


INTERVIEW_STATUS_SELECTION = [
    ('to_interview', 'Candidate to be interviewed'),
    ('internal_screening', 'Internal Screening'),
    ('round_1', 'Interview Round 1'),
    ('round_2', 'Interview Round 2'),
    ('selected', 'Selected'),
    ('placed', 'Placed'),
    ('rejected', 'Rejected'),
]


class HrRecruitmentCandidate(models.Model):
    _name = 'hr.recruitment.candidate'
    _description = 'Recruitment Interview Candidate'
    _order = 'create_date desc'
    _rec_name = 'name'

    requirement_id = fields.Many2one('hr.recruitment', string='Requirement', required=True, ondelete='cascade', index=True)
    code = fields.Char(string='Candidate Code', copy=False, readonly=True, default='New')

    name = fields.Char(string='Candidate Name', required=True)
    resume_data = fields.Binary(string='Resume', attachment=True)
    resume_filename = fields.Char(string='Resume Filename')

    current_salary = fields.Float(string='Current Salary (LPA)')
    expected_salary = fields.Float(string='Expected Salary (LPA)')
    email = fields.Char(string='Email ID')
    mobile = fields.Char(string='Mobile Number')
    current_location = fields.Char(string='Current Location')
    experience_years = fields.Float(string='Experience (Years)')
    notice_period = fields.Date(string='Notice Period')
    interview_status = fields.Selection(INTERVIEW_STATUS_SELECTION, string='Interview Status', default='to_interview', required=True)
    coordinator_id = fields.Many2one('hr.employee', string='Coordinator')
    closing_rate = fields.Float(string='Closing Rate (LPA)')
    deployed = fields.Boolean(string='Deployed')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('hr.recruitment.candidate') or 'New'
        return super().create(vals_list)
