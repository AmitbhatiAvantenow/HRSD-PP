from odoo import api, fields, models


class DocumentGenerated(models.Model):
    _name = 'document.generated'
    _description = 'Generated Document'
    _order = 'generated_date desc'
    _rec_name = 'code'

    code = fields.Char(required=True, copy=False, readonly=True, default='New')
    template_id = fields.Many2one('document.template', required=True, ondelete='restrict', index=True)
    partner_id = fields.Many2one('res.partner', string='Generated For')
    generated_by = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    generated_date = fields.Datetime(default=fields.Datetime.now, required=True)
    variable_values = fields.Text()

    file_data_pdf = fields.Binary(attachment=True)
    file_name_pdf = fields.Char()
    file_data_docx = fields.Binary(attachment=True)
    file_name_docx = fields.Char()

    status = fields.Selection([
        ('draft', 'Draft'), ('sent', 'Sent'), ('signed', 'Signed'),
    ], default='draft', required=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('document.generated') or 'New'
        return super().create(vals_list)

    def action_mark_sent(self):
        self.write({'status': 'sent'})

    def action_mark_signed(self):
        self.write({'status': 'signed'})

    @api.model
    def get_generated_documents_data(self):
        rows = self.search_read(
            [], ['code', 'template_id', 'partner_id', 'generated_by', 'generated_date',
                 'status', 'file_name_pdf', 'file_name_docx'],
        )
        for row in rows:
            row['download_pdf_url'] = (
                f"/web/content/document.generated/{row['id']}/file_data_pdf/{row['file_name_pdf']}?download=true"
                if row.get('file_name_pdf') else False
            )
            row['download_docx_url'] = (
                f"/web/content/document.generated/{row['id']}/file_data_docx/{row['file_name_docx']}?download=true"
                if row.get('file_name_docx') else False
            )
        return rows
