# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # Roll-ups to surface on the employee form
    document_tracker_ids = fields.One2many("mn.hr.document.tracker", "employee_id")
    document_count = fields.Integer(compute="_compute_plus_counts")
    expiring_document_count = fields.Integer(compute="_compute_plus_counts")
    asset_assignment_ids = fields.One2many("mn.hr.asset.assignment", "employee_id")
    active_asset_count = fields.Integer(compute="_compute_plus_counts")
    dependent_ids = fields.One2many("mn.hr.dependent", "employee_id")
    dependent_count = fields.Integer(compute="_compute_plus_counts")
    career_history_ids = fields.One2many("mn.hr.career.history", "employee_id")
    disciplinary_ids = fields.One2many("mn.hr.disciplinary.action", "employee_id")
    open_disciplinary_count = fields.Integer(compute="_compute_plus_counts")
    loan_ids = fields.One2many("mn.hr.loan", "employee_id")
    active_loan_count = fields.Integer(compute="_compute_plus_counts")
    probation_id = fields.Many2one("mn.hr.probation", compute="_compute_probation")

    # Extra fields nice to have on every employee
    work_permit_no = fields.Char(string="Work Permit Number")
    work_permit_expiry = fields.Date()
    iqama_no = fields.Char(string="Iqama / Residence ID")
    iqama_expiry = fields.Date()
    insurance_card_no = fields.Char()
    insurance_card_expiry = fields.Date()
    blood_type = fields.Char()

    def _compute_plus_counts(self):
        Doc = self.env["mn.hr.document.tracker"].sudo()
        Ast = self.env["mn.hr.asset.assignment"].sudo()
        Dep = self.env["mn.hr.dependent"].sudo()
        Dis = self.env["mn.hr.disciplinary.action"].sudo()
        Lo = self.env["mn.hr.loan"].sudo()
        for r in self:
            r.document_count = Doc.search_count([("employee_id", "=", r.id)])
            r.expiring_document_count = Doc.search_count([
                ("employee_id", "=", r.id),
                ("state", "in", ("warning", "critical")),
            ])
            r.active_asset_count = Ast.search_count([
                ("employee_id", "=", r.id), ("state", "=", "assigned")])
            r.dependent_count = Dep.search_count([("employee_id", "=", r.id)])
            r.open_disciplinary_count = Dis.search_count([
                ("employee_id", "=", r.id),
                ("state", "in", ("issued", "acknowledged"))])
            r.active_loan_count = Lo.search_count([
                ("employee_id", "=", r.id),
                ("state", "in", ("active", "disbursed"))])

    def _compute_probation(self):
        Prob = self.env["mn.hr.probation"].sudo()
        for r in self:
            r.probation_id = Prob.search([
                ("employee_id", "=", r.id),
                ("state", "in", ("active", "review_due"))], limit=1)
