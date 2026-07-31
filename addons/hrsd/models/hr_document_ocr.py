from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)


class HrDocumentOcr(models.Model):
    _name = 'hr.document.ocr'
    _description = 'HR OCR Document Scan'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Document Name', required=True, default='Untitled Scan')
    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='set null', index=True)
    document_type = fields.Selection([
        ('contract', 'Employment Contract'),
        ('passport', 'Passport / ID'),
        ('emirates_id', 'Emirates ID'),
        ('certificate', 'Certificate / Qualification'),
        ('payslip', 'Payslip'),
        ('visa', 'Visa Document'),
        ('form', 'HR Form'),
        ('other', 'Other'),
    ], string='Document Type', default='other', required=True)
    file_data = fields.Binary(string='Document File', attachment=True)
    file_name = fields.Char(string='File Name')
    file_size_kb = fields.Integer(string='File Size (KB)')
    # ir.attachment linked to the employee record
    employee_attachment_id = fields.Many2one(
        'ir.attachment', string='Employee Attachment',
        ondelete='set null', readonly=True,
        help='The scanned file as saved to the linked employee\'s attachments.'
    )
    extracted_text = fields.Text(string='Extracted Text')
    smart_fields = fields.Text(string='Detected Fields (JSON)')
    page_count = fields.Integer(string='Pages', default=1)
    word_count = fields.Integer(string='Word Count', compute='_compute_word_count', store=True)
    confidence = fields.Float(string='OCR Confidence (%)', digits=(5, 1))
    state = fields.Selection([
        ('done', 'Scanned'),
        ('error', 'Error'),
    ], default='done', string='Status', required=True)
    error_message = fields.Text(string='Error Details')
    scanned_by = fields.Many2one(
        'res.users', string='Scanned By',
        default=lambda self: self.env.user, readonly=True
    )
    notes = fields.Text(string='Notes')

    @api.depends('extracted_text')
    def _compute_word_count(self):
        for rec in self:
            rec.word_count = len((rec.extracted_text or '').split()) if rec.extracted_text else 0

    def get_smart_fields_dict(self):
        try:
            return json.loads(self.smart_fields or '{}')
        except Exception:
            return {}

    def action_open_employee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
