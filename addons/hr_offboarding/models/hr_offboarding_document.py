from odoo import fields, models


class HrOffboardingDocument(models.Model):
    _name = 'hr.offboarding.document'
    _description = 'Offboarding Document'
    _order = 'id desc'

    name = fields.Char(required=True)
    request_id = fields.Many2one('hr.offboarding.request', required=True, ondelete='cascade', index=True)
    document_type = fields.Selection([
        ('experience_letter', 'Experience Letter'),
        ('relieving_letter', 'Relieving Letter'),
        ('settlement_letter', 'Settlement Letter'),
        ('tax_certificate', 'Tax Certificate'),
        ('clearance_certificate', 'Clearance Certificate'),
        ('no_due_certificate', 'No Due Certificate'),
        ('service_certificate', 'Service Certificate'),
        ('salary_history', 'Salary History'),
        ('other', 'Other'),
    ], required=True, default='other')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], default='pending', required=True)
    datas = fields.Binary(string='File', attachment=True)
    datas_fname = fields.Char(string='Filename')
    issue_date = fields.Date()
    notes = fields.Text()
