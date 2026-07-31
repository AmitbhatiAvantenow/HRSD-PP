from odoo import fields, models


class DocumentTemplateTag(models.Model):
    _name = 'document.template.tag'
    _description = 'Document Template Tag'
    _order = 'name'

    name = fields.Char(required=True)
    color = fields.Integer(default=0)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Tag name must be unique.'),
    ]
