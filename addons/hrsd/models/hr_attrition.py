from odoo import models, fields


class HrAttritionSnapshot(models.Model):
    _name = 'hr.attrition.snapshot'
    _description = 'Employee Attrition Risk Snapshot'
    _order = 'snapshot_date desc, id desc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    snapshot_date = fields.Date(default=fields.Date.today, index=True)
    risk_score = fields.Float(digits=(6, 2))
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ])
    tenure_factor = fields.Float()
    age_factor = fields.Float()
    salary_factor = fields.Float()
    leave_factor = fields.Float()
    contract_factor = fields.Float()
    attendance_factor = fields.Float()
    skills_factor = fields.Float()
    top_factor = fields.Char()
    recommendations = fields.Text()
