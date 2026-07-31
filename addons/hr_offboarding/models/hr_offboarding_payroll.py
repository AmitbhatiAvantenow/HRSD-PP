from odoo import api, fields, models


class HrOffboardingPayroll(models.Model):
    _name = 'hr.offboarding.payroll'
    _description = 'Offboarding Full & Final Settlement'
    _order = 'id desc'

    request_id = fields.Many2one('hr.offboarding.request', required=True, ondelete='cascade', index=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    leave_encashment = fields.Monetary(currency_field='currency_id')
    pending_salary = fields.Monetary(currency_field='currency_id')
    bonus = fields.Monetary(currency_field='currency_id')
    incentives = fields.Monetary(currency_field='currency_id')
    gratuity = fields.Monetary(currency_field='currency_id')
    loans = fields.Monetary(currency_field='currency_id', help='Deduction: outstanding loans')
    recoveries = fields.Monetary(currency_field='currency_id', help='Deduction: other recoveries')
    tax = fields.Monetary(currency_field='currency_id', help='Deduction: tax')
    pf = fields.Monetary(currency_field='currency_id', help='Provident Fund contribution')

    total_earnings = fields.Monetary(currency_field='currency_id', compute='_compute_totals', store=True)
    total_deductions = fields.Monetary(currency_field='currency_id', compute='_compute_totals', store=True)
    net_settlement = fields.Monetary(currency_field='currency_id', compute='_compute_totals', store=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ], default='draft', required=True)
    notes = fields.Text()

    @api.depends('leave_encashment', 'pending_salary', 'bonus', 'incentives', 'gratuity',
                 'loans', 'recoveries', 'tax', 'pf')
    def _compute_totals(self):
        for rec in self:
            rec.total_earnings = rec.leave_encashment + rec.pending_salary + rec.bonus + rec.incentives + rec.gratuity
            rec.total_deductions = rec.loans + rec.recoveries + rec.tax + rec.pf
            rec.net_settlement = rec.total_earnings - rec.total_deductions
