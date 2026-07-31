# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HRLoan(models.Model):
    _name = "mn.hr.loan"
    _description = "Employee Loan"
    _inherit = ["mail.thread"]
    _order = "request_date desc"

    name = fields.Char(default=lambda s: s.env["ir.sequence"].next_by_code("mn.hr.loan") or "/",
        readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    request_date = fields.Date(default=fields.Date.today, required=True, tracking=True)
    purpose = fields.Selection([
        ("personal", "Personal"), ("medical", "Medical"),
        ("education", "Education"), ("housing", "Housing"),
        ("travel", "Travel"), ("emergency", "Emergency"),
        ("other", "Other"),
    ], default="personal")
    description = fields.Text()

    principal = fields.Monetary(currency_field="currency_id", required=True, tracking=True)
    interest_pct = fields.Float(default=0.0, help="Annual interest %.")
    months = fields.Integer(default=12, required=True)
    start_date = fields.Date(default=fields.Date.today, tracking=True)
    monthly_amount = fields.Monetary(compute="_compute_monthly", currency_field="currency_id", store=True)
    total_repayment = fields.Monetary(compute="_compute_monthly", currency_field="currency_id", store=True)

    installment_ids = fields.One2many("mn.hr.loan.installment", "loan_id")
    paid_amount = fields.Monetary(compute="_compute_paid", currency_field="currency_id", store=True)
    remaining_amount = fields.Monetary(compute="_compute_paid", currency_field="currency_id", store=True)

    state = fields.Selection([
        ("draft", "Draft"), ("submitted", "Submitted"),
        ("approved", "Approved"), ("rejected", "Rejected"),
        ("disbursed", "Disbursed"), ("active", "Active"),
        ("paid", "Fully paid"), ("closed", "Closed"),
    ], default="draft", tracking=True)
    approved_by_id = fields.Many2one("res.users", tracking=True)
    disbursed_on = fields.Date()
    currency_id = fields.Many2one("res.currency",
        default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
        related="employee_id.company_id", store=True)

    @api.depends("principal", "interest_pct", "months")
    def _compute_monthly(self):
        for r in self:
            if r.months and r.principal:
                interest = r.principal * (r.interest_pct / 100.0)
                total = r.principal + interest
                r.total_repayment = total
                r.monthly_amount = total / r.months
            else:
                r.total_repayment = 0
                r.monthly_amount = 0

    @api.depends("installment_ids.state", "installment_ids.amount")
    def _compute_paid(self):
        for r in self:
            paid = sum(r.installment_ids.filtered(lambda i: i.state == "paid").mapped("amount"))
            r.paid_amount = paid
            r.remaining_amount = r.total_repayment - paid

    def action_submit(self):
        self.write({"state": "submitted"})
    def action_approve(self):
        self.write({"state": "approved", "approved_by_id": self.env.user.id})
    def action_reject(self):
        self.write({"state": "rejected"})
    def action_disburse(self):
        for r in self:
            r._generate_installments()
            r.disbursed_on = fields.Date.today()
            r.state = "active"

    def _generate_installments(self):
        Inst = self.env["mn.hr.loan.installment"].sudo()
        for r in self:
            r.installment_ids.unlink()
            for i in range(r.months):
                due = (r.start_date or fields.Date.today()) + relativedelta(months=i)
                Inst.create({
                    "loan_id": r.id, "sequence": i + 1,
                    "due_date": due, "amount": r.monthly_amount,
                    "state": "pending",
                })


class HRLoanInstallment(models.Model):
    _name = "mn.hr.loan.installment"
    _description = "Loan Installment"
    _order = "due_date asc"

    loan_id = fields.Many2one("mn.hr.loan", required=True, ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", related="loan_id.employee_id", store=True)
    sequence = fields.Integer()
    due_date = fields.Date(required=True)
    amount = fields.Monetary(currency_field="currency_id", required=True)
    paid_amount = fields.Monetary(currency_field="currency_id")
    paid_on = fields.Date()
    state = fields.Selection([
        ("pending", "Pending"), ("paid", "Paid"),
        ("overdue", "Overdue"), ("waived", "Waived"),
    ], default="pending", compute="_compute_state", store=True)
    currency_id = fields.Many2one("res.currency",
        related="loan_id.currency_id", store=True)

    @api.depends("paid_on", "due_date")
    def _compute_state(self):
        today = fields.Date.today()
        for r in self:
            if r.paid_on: r.state = "paid"
            elif r.due_date and r.due_date < today: r.state = "overdue"
            else: r.state = "pending"

    def action_mark_paid(self):
        for r in self:
            r.paid_amount = r.amount
            r.paid_on = fields.Date.today()
