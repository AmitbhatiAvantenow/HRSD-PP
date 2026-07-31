import re

from odoo import api, fields, models


def slugify_key(name):
    return re.sub(r'_+', '_', re.sub(r'[^a-z0-9_]', '_', (name or '').strip().lower())).strip('_')


class DocumentTemplateVariable(models.Model):
    _name = 'document.template.variable'
    _description = 'Document Template Variable'
    _order = 'sequence, id'

    template_id = fields.Many2one('document.template', required=True, ondelete='cascade', index=True)
    name = fields.Char(required=True)
    key = fields.Char(required=True)
    variable_type = fields.Selection([
        ('text', 'Text'),
        ('long_text', 'Long Text'),
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('date', 'Date'),
        ('boolean', 'Yes/No'),
    ], default='text', required=True)
    default_value = fields.Char()
    is_required = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('key_uniq_per_template', 'unique(template_id, key)', 'Variable key must be unique within a template.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('key') and vals.get('name'):
                vals['key'] = slugify_key(vals['name'])
        return super().create(vals_list)
