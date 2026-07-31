from odoo import fields, models

DEPARTMENT_SELECTION = [
    ('real_estate', 'Real Estate'),
    ('hr', 'HR'),
    ('finance', 'Finance'),
    ('legal', 'Legal'),
    ('procurement', 'Procurement'),
    ('sales', 'Sales'),
    ('maintenance', 'Maintenance'),
    ('operations', 'Operations'),
    ('administration', 'Administration'),
    ('marketing', 'Marketing'),
]


class DocumentTemplateCategory(models.Model):
    _name = 'document.template.category'
    _description = 'Document Template Category'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    department = fields.Selection(DEPARTMENT_SELECTION, required=True)
    icon = fields.Char(default='fa-file-text-o')
    color = fields.Integer(default=0)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    template_count = fields.Integer(compute='_compute_template_count')

    def _compute_template_count(self):
        counts = dict(self.env['document.template']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count']))
        for rec in self:
            rec.template_count = counts.get(rec, 0)
