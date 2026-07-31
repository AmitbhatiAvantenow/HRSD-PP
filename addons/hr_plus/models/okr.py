# -*- coding: utf-8 -*-
"""Quarterly OKRs (Objectives + Key Results) with weekly check-ins."""
from odoo import api, fields, models


class OKR(models.Model):
    _name = "mn.hr.okr"
    _description = "OKR (Objective + Key Results)"
    _inherit = ["mail.thread"]
    _order = "period_year desc, period_quarter desc"

    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    manager_id = fields.Many2one("hr.employee",
        related="employee_id.parent_id", store=True)
    period_year = fields.Integer(required=True,
        default=lambda s: fields.Date.today().year)
    period_quarter = fields.Selection([
        ("Q1", "Q1"), ("Q2", "Q2"), ("Q3", "Q3"), ("Q4", "Q4"),
    ], required=True, default="Q1", tracking=True)
    description = fields.Text(help="Objective description — qualitative.")
    weight = fields.Float(default=1.0)
    key_result_ids = fields.One2many("mn.hr.okr.kr", "okr_id")
    progress_pct = fields.Float(compute="_compute_progress", store=True,
        string="Overall progress %")
    state = fields.Selection([
        ("draft", "Draft"), ("active", "Active"),
        ("achieved", "Achieved"), ("partial", "Partial"),
        ("missed", "Missed"), ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)
    self_score = fields.Float()
    manager_score = fields.Float()
    final_score = fields.Float(compute="_compute_final", store=True)
    notes = fields.Text()
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    @api.depends("key_result_ids.progress_pct")
    def _compute_progress(self):
        for r in self:
            if r.key_result_ids:
                r.progress_pct = sum(r.key_result_ids.mapped("progress_pct")) / len(r.key_result_ids)
            else:
                r.progress_pct = 0

    @api.depends("self_score", "manager_score")
    def _compute_final(self):
        for r in self:
            if r.self_score and r.manager_score:
                r.final_score = (r.self_score + r.manager_score) / 2
            else:
                r.final_score = r.manager_score or r.self_score


class KeyResult(models.Model):
    _name = "mn.hr.okr.kr"
    _description = "OKR Key Result"
    _order = "okr_id, sequence"

    okr_id = fields.Many2one("mn.hr.okr", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    target_value = fields.Float()
    current_value = fields.Float()
    unit = fields.Char(help="e.g. %, $, customers, etc.")
    progress_pct = fields.Float(compute="_compute_kr_progress", store=True)
    notes = fields.Char()

    @api.depends("target_value", "current_value")
    def _compute_kr_progress(self):
        for r in self:
            r.progress_pct = min(100, (r.current_value / r.target_value * 100)) if r.target_value else 0
