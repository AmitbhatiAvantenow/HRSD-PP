# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AssetCategory(models.Model):
    _name = "mn.hr.asset.category"
    _description = "Asset Category"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    icon = fields.Char(default="fa-laptop")
    serial_required = fields.Boolean(default=False)
    active = fields.Boolean(default=True)


class AssetAssignment(models.Model):
    _name = "mn.hr.asset.assignment"
    _description = "Asset Assignment"
    _inherit = ["mail.thread"]
    _order = "assigned_on desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.asset.assignment") or "/",
        readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    category_id = fields.Many2one("mn.hr.asset.category", required=True, tracking=True)
    asset_name = fields.Char(required=True, tracking=True,
        help="E.g. 'MacBook Pro 14, 2024' or 'iPhone 15 Pro 256GB'")
    serial_number = fields.Char()
    purchase_value = fields.Monetary(currency_field="currency_id")

    assigned_on = fields.Date(default=fields.Date.today, required=True, tracking=True)
    returned_on = fields.Date(tracking=True)
    condition_on_issue = fields.Selection([
        ("new", "New"), ("good", "Good"), ("used", "Used"),
    ], default="new")
    condition_on_return = fields.Selection([
        ("good", "Good"), ("damaged", "Damaged"), ("lost", "Lost"),
    ])
    handover_doc = fields.Binary(attachment=True, string="Signed handover form")
    notes = fields.Text()

    state = fields.Selection([
        ("assigned", "Assigned"),
        ("returned", "Returned"),
        ("damaged", "Damaged / Charge"),
        ("lost", "Lost / Charge"),
    ], default="assigned", tracking=True, compute="_compute_state", store=True)
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        default=lambda s: s.env.company)

    @api.depends("returned_on", "condition_on_return")
    def _compute_state(self):
        for r in self:
            if r.condition_on_return == "damaged": r.state = "damaged"
            elif r.condition_on_return == "lost": r.state = "lost"
            elif r.returned_on: r.state = "returned"
            else: r.state = "assigned"

    def action_return(self):
        for r in self:
            if not r.returned_on:
                r.returned_on = fields.Date.today()
