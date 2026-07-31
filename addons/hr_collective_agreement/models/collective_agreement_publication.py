# Copyright 2025 Ángel Rivas <angel.rivas@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CollectiveAgreementOfficialPublication(models.Model):
    _name = "collective.agreement.official.publication"
    _description = "Collective Agreement Official Publication"

    name = fields.Char(required=True)

    _name_uniq = models.Constraint("unique(name)", "The name must be unique.")
