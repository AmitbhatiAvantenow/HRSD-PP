# -*- coding: utf-8 -*-
from odoo import fields, models


class HrPayslipPayWizard(models.TransientModel):
    """Small confirmation dialog used to mark one or more validated
    payslips as paid, recording how and when they were paid."""
    _name = 'hr.payslip.pay.wizard'
    _description = 'Pay Payslip'

    payslip_ids = fields.Many2many('hr.payslip', string='Payslips',
                                   default=lambda self: self.env.context.get(
                                       'active_ids', []))
    payment_mode = fields.Selection([
        ('advice', 'Payment Advice'),
        ('neft', 'By NEFT'),
        ('cheque', 'By Cheque'),
    ], string='Mode', default='advice', required=True)
    payment_date = fields.Date(string='Payment Date', required=True,
                               default=fields.Date.context_today)

    def action_confirm(self):
        self.ensure_one()
        self.payslip_ids.action_payslip_pay(
            payment_mode=self.payment_mode, payment_date=self.payment_date)
        return {'type': 'ir.actions.act_window_close'}
