# -*- coding: utf-8 -*-
from odoo import fields, models


class Dependent(models.Model):
    _name = "mn.hr.dependent"
    _description = "Employee Dependent"
    _order = "employee_id, date_of_birth desc"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    name_ar = fields.Char(string="Name (Arabic)")
    relation = fields.Selection([
        ("spouse", "Spouse"), ("child", "Child"),
        ("parent", "Parent"), ("sibling", "Sibling"), ("other", "Other"),
    ], required=True)
    gender = fields.Selection([
        ("male", "Male"), ("female", "Female"),
    ])
    date_of_birth = fields.Date()
    nationality_id = fields.Many2one("res.country")
    passport_no = fields.Char()
    passport_expiry = fields.Date()
    visa_no = fields.Char()
    visa_expiry = fields.Date()
    eligible_allowance = fields.Boolean(string="Eligible for dependent allowance")
    school = fields.Char()
    notes = fields.Char()
