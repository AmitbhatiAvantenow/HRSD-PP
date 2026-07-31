from odoo import fields, models


class HrOnboardingDocument(models.Model):
    _name = 'hr.onboarding.document'
    _description = 'Onboarding Document'
    _order = 'id desc'

    name = fields.Char(required=True)
    onboarding_id = fields.Many2one('hr.onboarding', required=True, ondelete='cascade', index=True)
    document_type = fields.Selection([
        ('passport', 'Passport'),
        ('pan', 'PAN Card'),
        ('aadhaar', 'Aadhaar'),
        ('driving_license', 'Driving License'),
        ('education', 'Education Certificate'),
        ('experience', 'Experience Letter'),
        ('offer_letter', 'Offer Letter'),
        ('contract', 'Contract'),
        ('nda', 'NDA'),
        ('medical', 'Medical Report'),
        ('visa', 'Visa'),
        ('resume', 'Resume'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ], required=True, default='other')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('uploaded', 'Uploaded'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], default='pending', required=True)
    datas = fields.Binary(string='File', attachment=True)
    datas_fname = fields.Char(string='Filename')
    upload_date = fields.Datetime()
    expiry_date = fields.Date()
    notes = fields.Text()
