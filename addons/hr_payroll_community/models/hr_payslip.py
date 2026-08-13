# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from pytz import timezone
import babel

# This will generate 16th of days
ROUNDING_FACTOR = 16

# ASCII-safe stand-ins for currency symbols that some wkhtmltopdf
# installs can't render (see HrPayslip.format_currency). Falls back to
# the currency's own ISO code (e.g. 'INR') if not listed here.
ASCII_CURRENCY_LABELS = {
    'INR': 'Rs.',
}


class HrPayslip(models.Model):
    """Create new model for getting total Payroll Sheet for an Employee"""
    _name = 'hr.payslip'
    _inherit = ['mail.thread.main.attachment']
    _description = 'Pay Slip'

    struct_id = fields.Many2one(comodel_name='hr.payroll.structure',
                                string='Structure',
                                help='Defines the rules that have to be applied'
                                     ' to this payslip, accordingly '
                                     'to the contract chosen. If you let empty '
                                     'the field contract, this field isn\'t '
                                     'mandatory anymore and thus the rules '
                                     'applied will be all the rules set on the '
                                     'structure of all contracts of the '
                                     'employee valid for the chosen period')
    name = fields.Char(string='Payslip Name', help="Enter Payslip Name")
    number = fields.Char(string='Reference', copy=False,
                         help="References for Payslip", )
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',
                                  required=True,
                                  help="Choose Employee for Payslip")
    date_from = fields.Date(string='Date From', required=True,
                            help="Start date for Payslip",
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          help="End date for Payslip",
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1,
                                                              days=-1)).date()))
    # this is chaos: 4 states are defined, 3 are used ('verify' isn't)
    # and 5 exist ('confirm' seems to have existed)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, 
                the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('hr.payslip.line',
                               'slip_id',
                               string='Payslip Lines',
                               help="Choose Payslip for line")

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company.id
    )
    worked_days_line_ids = fields.One2many('hr.payslip.worked.days',
                                           'payslip_id',
                                           string='Payslip Worked Days',
                                           copy=True,
                                           help="Payslip worked days for line")
    input_line_ids = fields.One2many('hr.payslip.input',
                                     'payslip_id',
                                     string='Payslip Inputs',
                                     help="Choose Payslip Input")
    paid = fields.Boolean(string='Made Payment Order ? ',
                          copy=False, help="Is Payment Order")
    date_paid = fields.Date(string='Payment Date', copy=False)
    payment_mode = fields.Selection([
        ('advice', 'Payment Advice'),
        ('neft', 'By NEFT'),
        ('cheque', 'By Cheque'),
    ], string='Payment Mode', copy=False)
    display_state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string='Payslip Status', compute='_compute_display_state', store=True)
    note = fields.Text(string='Internal Note', help="Description for Payslip")
    contract_id = fields.Many2one('hr.version', string='Contract',
                                  help="Choose Contract for Payslip")
    details_by_salary_rule_category_ids = fields.One2many(
        comodel_name='hr.payslip.line',
        compute='_compute_details_by_salary_rule_category_ids',
        string='Details by Salary Rule Category', help="Details from the salary"
                                                       " rule category")
    credit_note = fields.Boolean(string='Credit Note',
                                 help="Indicates this payslip has "
                                      "a refund of another")
    payslip_run_id = fields.Many2one('hr.payslip.run',
                                     string='Payslip Batches',
                                     copy=False, help="Choose Payslip Run")
    payslip_count = fields.Integer(compute='_compute_payslip_count',
                                   string="Payslip Computation Details",
                                   help="Set Payslip Count")

    def _compute_details_by_salary_rule_category_ids(self):
        """Compute function for Salary Rule Category for getting
         all Categories"""
        for payslip in self:
            payslip.details_by_salary_rule_category_ids = payslip.mapped(
                'line_ids').filtered(lambda line: line.category_id)

    def _compute_payslip_count(self):
        """Compute function for getting Total count of Payslips"""
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    @api.depends('state', 'paid')
    def _compute_display_state(self):
        """Friendlier Draft -> Validated -> Paid status, layered on top
        of the underlying draft/done/cancel state + paid flag."""
        for payslip in self:
            if payslip.state == 'cancel':
                payslip.display_state = 'cancel'
            elif payslip.paid:
                payslip.display_state = 'paid'
            elif payslip.state == 'done':
                payslip.display_state = 'validated'
            else:
                payslip.display_state = 'draft'

    def _attach_payslip_report(self):
        """Render the payslip report and post it as a message attachment,
        which Odoo automatically promotes to message_main_attachment_id -
        that's what powers the standard o_attachment_preview panel next
        to the form (the same mechanism used by Invoices/Bills)."""
        for payslip in self:
            pdf_content, _fmt = self.env['ir.actions.report']._render_qweb_pdf(
                'hr_payroll_community.report_payslip', payslip.ids)
            attachment = self.env['ir.attachment'].create({
                'name': '%s.pdf' % (payslip.name or payslip.number or 'Payslip'),
                'type': 'binary',
                'raw': pdf_content,
                'res_model': payslip._name,
                'res_id': payslip.id,
                'mimetype': 'application/pdf',
            })
            payslip.message_post(attachment_ids=[attachment.id])

    def _render_payslip_mail(self, template):
        """Substitute {{employee_name}}/{{month}}/{{net_pay}}/
        {{designation}}/{{company_name}} placeholders in the given
        hr.payslip.mail.template's subject/body for this one payslip.
        Plain string replacement (no Jinja/expression eval) - the
        wizard's "Manage Template" panel is meant for anyone with
        payroll access to edit safely, not just developers."""
        self.ensure_one()
        values = {
            '{{employee_name}}': self.employee_id.name or '',
            '{{month}}': self.date_from.strftime('%B %Y') if self.date_from else '',
            '{{net_pay}}': self.format_currency(self.get_salary_line_total('NET')),
            '{{company_name}}': self.company_id.name or '',
            '{{designation}}': self.employee_id.job_title or self.employee_id.job_id.name or '',
        }
        subject = template.subject or ''
        body = template.body or ''
        for token, val in values.items():
            subject = subject.replace(token, val)
            body = body.replace(token, val)
        return subject, body

    def action_send_payslip_email(self):
        """Email this payslip's PDF to the employee's work email, using
        the single shared hr.payslip.mail.template (subject/body/CC -
        editable from the New Payslip wizard's "Manage Template"
        button)."""
        self.ensure_one()
        if not self.employee_id.work_email:
            raise UserError(_('%s has no work email set - cannot send the payslip.') % self.employee_id.name)
        template = self.env['hr.payslip.mail.template'].sudo().get_or_create()
        subject, body = self._render_payslip_mail(template)
        pdf_content, _fmt = self.env['ir.actions.report']._render_qweb_pdf(
            'hr_payroll_community.report_payslip', self.ids)
        attachment = self.env['ir.attachment'].create({
            'name': '%s_%s_Payslip.pdf' % (
                (self.employee_id.name or 'Employee').replace(' ', '_'),
                self.date_from.strftime('%B_%Y') if self.date_from else 'Payslip'),
            'type': 'binary',
            'raw': pdf_content,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        mail_vals = {
            'subject': subject or _('Payslip'),
            'body_html': (body or '').replace('\n', '<br/>'),
            'email_to': self.employee_id.work_email,
            'attachment_ids': [(6, 0, [attachment.id])],
            'auto_delete': True,
        }
        if template.cc:
            mail_vals['email_cc'] = template.cc
        self.env['mail.mail'].sudo().create(mail_vals).send()
        return True

    @api.model
    def bulk_send_payslip_email(self, slip_ids):
        """Email every one of the given payslips to its employee,
        skipping (and reporting) any with no work email or a send
        failure - the bulk-mode "Send by Email" action on the New
        Payslip wizard's success screen."""
        results = []
        for slip in self.browse(slip_ids):
            try:
                slip.action_send_payslip_email()
                results.append({'slip_id': slip.id, 'status': 'sent'})
            except Exception as e:
                results.append({'slip_id': slip.id, 'status': 'error', 'reason': str(e)})
        return results

    def action_payslip_pay(self, payment_mode=False, payment_date=False):
        """Mark the payslip(s) as paid."""
        for payslip in self:
            if payslip.state != 'done':
                raise UserError(
                    _('Only validated payslips can be marked as paid.'))
        self.write({
            'paid': True,
            'payment_mode': payment_mode or self[:1].payment_mode or 'advice',
            'date_paid': payment_date or fields.Date.today(),
        })
        return True

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Function for adding constrains for payslip datas
        by considering date_from and date_to fields"""
        if any(self.filtered(
                lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(
                _("Payslip 'Date From' must be earlier 'Date To'."))

    def action_payslip_draft(self):
        """Function for change stage of Payslip"""
        return self.write({'state': 'draft'})

    def action_payslip_done(self):
        """Function for change stage of Payslip"""
        self.action_compute_sheet()
        for payslip in self:
            if not payslip.line_ids:
                raise UserError(_(
                    "%s has no computed salary lines - this employee has "
                    "no Salary Structure configured (or the structure has "
                    "no rules). Set a Salary Structure and Wage on the "
                    "employee's Payroll tab, then Compute again before "
                    "validating."
                ) % payslip.employee_id.name)
        res = self.write({'state': 'done'})
        self._attach_payslip_report()
        return res

    def action_payslip_cancel(self):
        """Function for change stage of Payslip"""
        return self.write({'state': 'cancel'})

    def action_refund_sheet(self):
        """Function for refund the Payslip sheet"""
        for payslip in self:
            copied_payslip = payslip.copy(
                {'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.action_compute_sheet()
            copied_payslip.action_payslip_done()
        formview_ref = self.env.ref('hr_payroll_community.hr_payslip_view_form',
                                    False)
        treeview_ref = self.env.ref('hr_payroll_community.hr_payslip_view_tree',
                                    False)
        return {
            'name': _("Refund Payslip"),
            'view_mode': 'list, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'list'),
                      (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    def unlink(self):
        """Function for unlink the Payslip"""
        if any(self.filtered(
                lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(
                _('You cannot delete a payslip which is not draft or cancelled!'
                  ))
        return super(HrPayslip, self).unlink()

    def action_recompute_worked_days(self):
        """Pull worked days/inputs fresh from the contract (Timesheet Pro
        attendance + Time Off) and recompute the salary lines. The
        interactive form does this automatically through onchange as
        soon as employee/dates are set, but payslips created headlessly
        (imports, demo data, automation) never trigger onchange, so this
        gives an explicit, idempotent way to (re)pull everything and
        compute in one call."""
        for payslip in self:
            if payslip.state != 'draft':
                raise UserError(_('Only draft payslips can be recomputed.'))
            contract = payslip.contract_id
            if not contract:
                contract_ids = self.get_contract(
                    payslip.employee_id, payslip.date_from, payslip.date_to)
                contract = self.env['hr.version'].browse(contract_ids[:1])
            if not contract:
                raise UserError(_(
                    'No contract found for %s over this period.'
                ) % payslip.employee_id.name)
            if payslip.contract_id != contract:
                payslip.contract_id = contract.id
            if not payslip.struct_id:
                payslip.struct_id = contract.struct_id.id
            worked_days_line_ids = self.get_worked_day_lines(
                contract, payslip.date_from, payslip.date_to)
            input_line_ids = self.get_inputs(
                contract, payslip.date_from, payslip.date_to)
            payslip.worked_days_line_ids.unlink()
            payslip.input_line_ids.unlink()
            payslip.write({
                'worked_days_line_ids': [
                    (0, 0, line) for line in worked_days_line_ids],
                'input_line_ids': [
                    (0, 0, line) for line in input_line_ids],
            })
        self.action_compute_sheet()
        return True

    @api.model
    def find_duplicate_payslip(self, employee_id, date_from, date_to):
        """Look for an existing (non-cancelled) payslip for this employee
        whose period overlaps the requested one, so the New Payslip
        wizard can warn the user instead of silently creating a
        duplicate. Returns a summary dict, or False if none found."""
        existing = self.search([
            ('employee_id', '=', employee_id),
            ('state', '!=', 'cancel'),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
        ], order='date_from', limit=1)
        if not existing:
            return False
        return {
            'id': existing.id,
            'number': existing.number or _('Draft'),
            'state': existing.state,
            'date_from': fields.Date.to_string(existing.date_from),
            'date_to': fields.Date.to_string(existing.date_to),
        }

    @api.model
    def check_bulk_duplicates(self, employee_ids, date_from, date_to):
        """Pre-flight duplicate check for the whole selected batch, so
        the New Payslip wizard can warn ("N of these already have a
        payslip for this period") and let the user choose - skip them,
        or create duplicates anyway - *before* generating, instead of
        silently skipping and leaving the user guessing why fewer
        payslips came out than employees were selected."""
        conflicts = []
        for employee in self.env['hr.employee'].browse(employee_ids):
            duplicate = self.find_duplicate_payslip(
                employee.id, date_from, date_to)
            if duplicate:
                conflicts.append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'slip_id': duplicate['id'],
                    'number': duplicate['number'],
                    'state': duplicate['state'],
                })
        return conflicts

    @api.model
    def bulk_generate(self, employee_ids, date_from, date_to, run_name=None,
                       force=False):
        """Create + compute a draft payslip for every one of the given
        employees over the same period, for the New Payslip wizard's
        bulk mode ("generate for several/all employees at once"). Every
        created payslip is grouped into a new hr.payslip.run batch.
        Unless force=True (user explicitly chose "Create Duplicates
        Anyway" after check_bulk_duplicates warned them), employees who
        already have an overlapping payslip are skipped, not duplicated;
        employees with no usable contract/structure are reported as
        errors. One employee failing never aborts the rest - each is
        isolated behind its own savepoint.
        Returns {'run_id': int|False, 'results': [ {...} ]}."""
        run = self.env['hr.payslip.run'].create({
            'name': run_name or _('Bulk Payslips %s → %s') % (
                date_from, date_to),
            'date_start': date_from,
            'date_end': date_to,
        })
        results = []
        for employee in self.env['hr.employee'].browse(employee_ids):
            duplicate = None if force else self.find_duplicate_payslip(
                employee.id, date_from, date_to)
            if duplicate:
                results.append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'status': 'skipped',
                    'reason': _('Payslip %s already exists for this '
                               'period') % duplicate['number'],
                    'slip_id': duplicate['id'],
                })
                continue
            try:
                with self.env.cr.savepoint():
                    slip = self.create({
                        'employee_id': employee.id,
                        'date_from': date_from,
                        'date_to': date_to,
                        'payslip_run_id': run.id,
                    })
                    slip.action_recompute_worked_days()
                    net_line = slip.line_ids.filtered(
                        lambda l: l.code == 'NET')
                    results.append({
                        'employee_id': employee.id,
                        'employee_name': employee.name,
                        'status': 'created',
                        'slip_id': slip.id,
                        'number': slip.number,
                        'net_total': sum(net_line.mapped('total')),
                    })
            except Exception as e:
                results.append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'status': 'error',
                    'reason': str(e),
                })
        if not any(r['status'] == 'created' for r in results):
            run.unlink()
            return {'run_id': False, 'results': results}
        return {'run_id': run.id, 'results': results}

    @api.model
    def bulk_validate(self, slip_ids):
        """Validate each of the given payslips independently - e.g. one
        employee with no computed lines (no Salary Structure configured)
        must not block the rest of the batch from being validated. Each
        payslip is isolated behind its own savepoint. Returns a list of
        {'slip_id', 'status': 'validated'|'error', 'net_total'?, 'reason'?}."""
        results = []
        for slip in self.browse(slip_ids):
            try:
                with self.env.cr.savepoint():
                    slip.action_payslip_done()
                    net_line = slip.line_ids.filtered(
                        lambda l: l.code == 'NET')
                    results.append({
                        'slip_id': slip.id,
                        'status': 'validated',
                        'net_total': sum(net_line.mapped('total')),
                    })
            except Exception as e:
                results.append({
                    'slip_id': slip.id,
                    'status': 'error',
                    'reason': str(e),
                })
        return results

    @api.model
    def bulk_set_worked_days(self, slip_ids, code, field, value):
        """Set one worked-days field (number_of_days/number_of_hours) for
        the line with the given code, across every one of the given
        payslips, then recompute each - the wizard's "Bulk Edit" action
        on the multi-employee Worked Days table."""
        if field not in ('number_of_days', 'number_of_hours'):
            raise UserError(_('Invalid field: %s') % field)
        slips = self.browse(slip_ids)
        for slip in slips:
            line = slip.worked_days_line_ids.filtered(
                lambda l: l.code == code)
            if line:
                line.write({field: value})
        slips.action_compute_sheet()
        return True

    @api.model
    def bulk_set_input(self, slip_ids, code, amount, name=None):
        """Set one payslip input to the same amount across every one of
        the given payslips, creating the input line where it doesn't
        exist yet, then recompute each.

        Used both for the fixed "for all selected employees" inputs
        (Bonus/TDS/Additional Deduction) and, from the New Payslip
        wizard's bulk Earnings/Deductions steps, to override an
        auto-computed line (e.g. 'BASIC_ADJ') on a single payslip (when
        slip_ids has one id) or to create/rename/amend an ad-hoc
        EXTRAEARN_*/EXTRADED_* line across the whole batch (when name is
        given - falls back to the matching hr.rule.input's label, or the
        raw code, for the fixed inputs that don't pass one)."""
        slips = self.browse(slip_ids)
        input_def = self.env['hr.rule.input'].search(
            [('code', '=', code)], limit=1)
        default_name = name or (input_def.name if input_def else code)
        for slip in slips:
            line = slip.input_line_ids.filtered(lambda l: l.code == code)
            if line:
                vals = {'amount': amount}
                if name:
                    vals['name'] = name
                line.write(vals)
            elif slip.contract_id:
                slip.write({'input_line_ids': [(0, 0, {
                    'name': default_name,
                    'code': code,
                    'amount': amount,
                    'contract_id': slip.contract_id.id,
                    'date_from': slip.date_from,
                    'date_to': slip.date_to,
                })]})
        slips.action_compute_sheet()
        return True

    @api.model
    def bulk_remove_input(self, slip_ids, code):
        """Remove the input line with the given code from every one of
        the given payslips - the bulk-mode equivalent of the "+ Add
        Earning"/"+ Add Deduction" line's trash-can button in the
        single-employee wizard - then recompute each."""
        slips = self.browse(slip_ids)
        slips.mapped('input_line_ids').filtered(lambda l: l.code == code).unlink()
        slips.action_compute_sheet()
        return True

    # TODO move this function into hr_contract module, on hr.employee object
    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date_field
        @param date_to: date_field
        @return: returns the ids of all the contracts for the given employee
        that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to),
                    ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to),
                    ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the
        # date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|',
                    ('date_end', '=', False), ('date_end', '>=', date_to)]

        clause_final = [('employee_id', '=', employee.id), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.version'].search(clause_final).ids

    def action_compute_sheet(self):
        """Function for compute Payslip sheet"""
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code(
                'salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be
            # for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                           self.get_contract(payslip.employee_id,
                                             payslip.date_from, payslip.date_to)
            payslip._backfill_missing_inputs(contract_ids)
            payslip._backfill_missing_worked_days(contract_ids)
            lines = [(0, 0, line) for line in
                     self._get_payslip_lines(contract_ids, payslip.id)]
            payslip.write({'line_ids': lines, 'number': number})
        return True

    def _backfill_missing_inputs(self, contract_ids):
        """Make sure every input the resolved structure's rules expect
        (Bonus, TDS, ...) actually exists as an hr.payslip.input line,
        without touching ones the user already filled in. Onchange
        normally creates these when the employee/dates are first picked
        in the form, but if the employee's Salary Structure is set (or
        changed) afterwards - or the payslip was created headlessly -
        those lines can be missing when Compute runs."""
        self.ensure_one()
        if not contract_ids:
            return
        contracts = self.env['hr.version'].browse(contract_ids)
        existing_codes = set(self.input_line_ids.mapped('code'))
        missing = [
            line for line in self.get_inputs(
                contracts, self.date_from, self.date_to)
            if line['code'] not in existing_codes
        ]
        if missing:
            self.write({
                'input_line_ids': [(0, 0, line) for line in missing]})

    def _backfill_missing_worked_days(self, contract_ids):
        """Same idea as _backfill_missing_inputs, for worked days: if the
        payslip has none yet (created headlessly, or before an employee
        had a working schedule), pull them from Timesheet Pro/Time Off/
        calendar so the salary rules always have WORKING_DAYS/WORK100/
        PAID_DAYS to work with instead of crashing on a missing name."""
        self.ensure_one()
        if self.worked_days_line_ids or not contract_ids:
            return
        contracts = self.env['hr.version'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(
            contracts, self.date_from, self.date_to)
        if worked_days_line_ids:
            self.write({
                'worked_days_line_ids': [
                    (0, 0, line) for line in worked_days_line_ids]})

    @api.model
    def _get_timesheet_pro_attendance(self, contract, date_from, date_to):
        """Return {'days': x, 'hours': y} of APPROVED HR Timesheet Pro
        hours logged by the contract's employee within the given period,
        or None if the timesheet_sheet model isn't installed or the
        employee has no approved timesheet overlapping the period.
        """
        Sheet = self.env.get('hr.timesheet.sheet')
        if Sheet is None:
            return None
        date_from = fields.Date.to_string(fields.Date.from_string(date_from))
        date_to = fields.Date.to_string(fields.Date.from_string(date_to))
        sheets = Sheet.sudo().search([
            ('employee_id', '=', contract.employee_id.id),
            ('state', '=', 'approved'),
            ('date_start', '<=', date_to),
            ('date_end', '>=', date_from),
        ])
        if not sheets:
            return None
        lines = sheets.line_ids.filtered(
            lambda line: line.date and date_from <= str(line.date) <= date_to)
        if not lines:
            return None
        hours = sum(lines.mapped('hours'))
        hours_per_day = contract.resource_calendar_id.hours_per_day or 8.0
        return {'days': hours / hours_per_day if hours_per_day else 0.0,
                'hours': hours}

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contracts: Browse record of contracts, date_from, date_to
        @return: returns a list of dict containing the input that should be
        applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(
                lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from),
                                        time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to),
                                      time.max)
            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=contract.resource_calendar_id)
            multi_leaves = []
            for day, hours, leave in day_leave_intervals:
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if len(leave) > 1:
                    for each in leave:
                        if each.holiday_id:
                            multi_leaves.append(each.holiday_id)
                else:
                    holiday = leave.holiday_id
                    current_leave_struct = leaves.setdefault(
                        holiday.holiday_status_id, {
                            'name': holiday.holiday_status_id.name or _(
                                'Global Leaves'),
                            'sequence': 5,
                            'code': holiday.holiday_status_id.code or 'GLOBAL',
                            'number_of_days': 0.0,
                            'number_of_hours': 0.0,
                            'contract_id': contract.id,
                        })
                    current_leave_struct['number_of_hours'] += hours
                    if work_hours:
                        current_leave_struct[
                            'number_of_days'] += hours / work_hours
            # compute worked days from approved HR Timesheet Pro hours for
            # the period. If nothing was actually logged, do NOT assume
            # full attendance - that would silently pay for days nobody
            # recorded as worked. Leave it at 0; a real figure has to come
            # from timesheets, approved Time Off, or a manual worked-days
            # line (Add Line in the New Payslip wizard).
            work_data = self._get_timesheet_pro_attendance(
                contract, date_from, date_to)
            from_timesheet = work_data is not None
            if work_data is None:
                work_data = {'days': 0.0, 'hours': 0.0}
            attendances = {
                'name': _("Timesheet Attendance") if from_timesheet else _(
                    "No Approved Timesheet Found (0 days)"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }
            res.append(attendances)
            uniq_leaves = [*set(multi_leaves)]
            c_leaves = {}
            for rec in uniq_leaves:
                duration = rec.duration_display.replace("days", "").strip()
                duration_in_hours = float(duration) * 24
                c_leaves.setdefault(rec.holiday_status_id,
                                    {'hours': duration_in_hours})
            for item in c_leaves:
                if not leaves or item not in leaves:
                    data = {
                        'name': item.name,
                        'sequence': 20,
                        'code': item.code or 'LEAVES',
                        'number_of_hours': c_leaves[item]['hours'],
                        'number_of_days': c_leaves[item][
                                              'hours'] / work_hours,
                        'contract_id': contract.id,
                    }
                    res.append(data)
                for time_off in leaves:
                    if item == time_off:
                        leaves[item]['number_of_hours'] += c_leaves[item][
                            'hours']
                        leaves[item]['number_of_days'] \
                            += c_leaves[item]['hours'] / work_hours
            res.extend(leaves.values())
            # Working days used as the pro-ration denominator must be the
            # FULL calendar month's schedule, not the requested slice:
            # otherwise a short/partial payslip (new joiner, exit, or any
            # custom period shorter than a month) always measures "days
            # worked" against "days scheduled" over that same short
            # window, so a fully-attended short period yields ratio == 1
            # and gets paid a FULL month's Basic/HRA/etc. regardless of
            # how few days the payslip actually covers.
            month_start = fields.Date.from_string(date_from).replace(day=1)
            month_end = month_start + relativedelta(months=1, days=-1)
            month_from = datetime.combine(month_start, time.min)
            month_to = datetime.combine(month_end, time.max)
            scheduled = contract.employee_id.get_work_days_data(
                month_from, month_to, calendar=calendar, compute_leaves=False)
            leave_days = sum(line['number_of_days'] for line in leaves.values())
            leave_hours = sum(line['number_of_hours'] for line in leaves.values())
            res.append({
                'name': _("Working Days in Period"),
                'sequence': 0,
                'code': 'WORKING_DAYS',
                'number_of_days': scheduled['days'],
                'number_of_hours': scheduled['hours'],
                'contract_id': contract.id,
            })
            res.append({
                'name': _("Total Paid Days"),
                'sequence': 30,
                'code': 'PAID_DAYS',
                'number_of_days': work_data['days'] - leave_days,
                'number_of_hours': work_data['hours'] - leave_hours,
                'contract_id': contract.id,
            })
        return res

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        """Function for getting contracts upon date_from and date_to fields"""
        res = []
        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(
            structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in
                           sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped(
            'input_ids')
        for contract in contracts:
            for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                    'date_from': date_from,
                    'date_to': date_to,
                }
                res.append(input_data)
        return res

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        """Function for getting Payslip Lines"""

        def _sum_salary_rule_category(localdict, category, amount):
            """Function for getting total sum of Salary Rule Category"""
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict,
                                                      category.parent_id,
                                                      amount)
            localdict['categories'].dict[category.code] \
                = category.code in localdict[
                'categories'].dict and localdict['categories'].dict[
                      category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            """Class for Browsable Object"""

            def __init__(self, employee_id, dict, env):
                """Function for getting employee_id,dict and env"""
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                """Function for return dict"""
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date,
                                        code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def _sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip days with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, 
                    sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date,
                                        code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip hours with respect to
                 from_date,to_date fields"""
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = 
                False then (pl.total) else (-pl.total) end)
                FROM hr_payslip as hp, hr_payslip_line as pl
                WHERE hp.employee_id = %s AND hp.state = 'done'
                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id 
                = pl.slip_id AND pl.code = %s""",
                                    (
                                        self.employee_id, from_date, to_date,
                                        code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten
        # by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line
        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict,
                                 self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)
        baselocaldict = {'categories': categories, 'rules': rules,
                         'payslip': payslips, 'worked_days': worked_days,
                         'inputs': inputs}
        # get the ids of the structures on the contracts and their
        # parent id as well
        contracts = self.env['hr.version'].browse(contract_ids)
        # Resolve which structure(s) to apply: the structure pinned on the
        # payslip itself wins (this is what onchange_employee/the demo
        # data sets), then the contract's own struct_id, then a linked
        # contract template's structure, as a last resort.
        if payslip.struct_id:
            structure_ids = list(
                set(payslip.struct_id._get_parent_structure().ids))
        elif len(contracts) == 1 and contracts.struct_id:
            structure_ids = list(
                set(contracts.struct_id._get_parent_structure().ids))
        elif len(contracts) == 1 and payslip.contract_id.contract_template_id.struct_id:
            structure_ids = list(
                set(payslip.contract_id.contract_template_id.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(
            structure_ids).get_all_rules()
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in
                           sorted(rule_ids, key=lambda x: x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee,
                             contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                # check if the rule can be applied
                if rule._satisfy_condition(
                        localdict) and rule.id not in blacklist:
                    # compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[
                        rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in
                    # the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(
                        localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in
                                  rule._recursive_search_of_rules()]
        return list(result_dict.values())


    def onchange_employee_id(self, date_from, date_to, employee_id=False,
                             contract_id=False):
        """Function for return worked days when changing onchange_employee_id"""
        # defaults
        res = {
            'value': {
                'line_ids': [],
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                'worked_days_line_ids': [(2, x,) for x in
                                         self.worked_days_line_ids.ids],
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (
                employee.name, tools.ustr(
                    babel.dates.format_date(date=ttyme, format='MMMM-y',
                                            locale=locale))),
            'company_id': employee.company_id.id,
        })
        if not self.env.context.get('contract'):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill
                # should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)
        if not contract_ids:
            return res
        contract = self.env['hr.version'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        # computation of the salary input
        contracts = self.env['hr.version'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.onchange('employee_id', )
    def onchange_employee(self):
        """Function for getting contract for employee"""
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.name = _('Salary Slip of %s for %s') % (
            employee.name, tools.ustr(
                babel.dates.format_date(date=ttyme, format='MMMM-y',
                                        locale=locale)))
        self.company_id = employee.company_id
        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.env['hr.version'].browse(contract_ids[0])
            struct = (self.contract_id.struct_id
                     or self.contract_id.contract_template_id.struct_id)
            if not struct:
                return
            self.struct_id = struct
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # computation of the salary input
        contracts = self.env['hr.version'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        return

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        """Function for getting structure when changing contract"""
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    def get_salary_line_total(self, code):
        """Function for getting total salary line"""
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0

    def get_worked_days_total(self, code):
        """Return the number of days recorded on the worked-days line
        with the given code (e.g. 'WORKING_DAYS', 'WORK100', 'PAID_DAYS')."""
        self.ensure_one()
        line = self.worked_days_line_ids.filtered(
            lambda wd: wd.code == code)
        return sum(line.mapped('number_of_days'))

    def get_leaves_days_total(self):
        """Return the total number of paid leave days deducted from
        Time Off for this payslip's period (excludes attendance/aggregate
        worked-days lines)."""
        self.ensure_one()
        lines = self.worked_days_line_ids.filtered(
            lambda wd: wd.code not in ('WORK100', 'WORKING_DAYS', 'PAID_DAYS'))
        return sum(lines.mapped('number_of_days'))

    def get_report_earning_lines(self):
        """Earnings shown on the payslip PDF's Earnings column: the
        auto-computed salary-rule lines (Basic, CCA+HRA, Medical,
        Project Allowance, ...) plus each "+ Add Earning" ad-hoc line by
        its own typed name/amount - not the single summed "Other
        Earnings" rule line (OTHERERN in
        hr_payroll_structure_india_regular.xml), which would otherwise
        replace every custom name the user typed with "Other Earnings".
        Bonus is reported separately (see the "Bonus if any" row), so
        it's excluded here too."""
        self.ensure_one()
        lines = self.line_ids.filtered(
            lambda l: l.appears_on_payslip and l.total
            and l.category_id.code not in ('DED', 'COMP', 'BONUS')
            and l.code not in ('GROSS', 'NET', 'CTC', 'OTHERERN'))
        result = [{'name': l.name, 'amount': l.total} for l in lines]
        extra = self.input_line_ids.filtered(
            lambda i: i.code and i.code.startswith('EXTRAEARN') and i.amount)
        result += [{'name': i.name, 'amount': i.amount} for i in extra]
        return result

    def get_report_deduction_lines(self):
        """Deductions shown on the payslip PDF's Deductions column: same
        idea as get_report_earning_lines but for EPF/LWF-style lines -
        each "+ Add Deduction" ad-hoc line is listed by its own name
        instead of being folded into "Other Deductions" (OTHERDED). TDS
        and Additional Deduction are reported separately (see the "if
        any" rows), so they're excluded here too. Amounts are returned
        as positive magnitudes (line.total is negative internally)."""
        self.ensure_one()
        lines = self.line_ids.filtered(
            lambda l: l.appears_on_payslip and l.total
            and l.category_id.code == 'DED'
            and l.code not in ('TDSAMT', 'ADDLDEDAMT', 'OTHERDED'))
        result = [{'name': l.name, 'amount': -l.total} for l in lines]
        extra = self.input_line_ids.filtered(
            lambda i: i.code and i.code.startswith('EXTRADED') and i.amount)
        result += [{'name': i.name, 'amount': i.amount} for i in extra]
        return result

    @api.model
    def bulk_set_note(self, slip_ids, note):
        """Set the Remarks (note) field to the same text across every
        one of the given payslips - the bulk-mode "Remarks for all
        selected employees" input in the New Payslip wizard's Review
        step. No recompute needed: note doesn't feed into any salary
        rule."""
        self.browse(slip_ids).write({'note': note})
        return True

    def format_currency(self, amount):
        """Plain-text currency formatting for the payslip report.

        Deliberately avoids the currency's Unicode symbol (e.g. the ₹
        Rupee sign, U+20B9): on some wkhtmltopdf installs that glyph is
        missing from every font wkhtmltopdf's bundled renderer can see,
        and instead of leaving a blank box for just that character, it
        blanks the surrounding text too. A plain ASCII code (e.g. "Rs.",
        "INR") renders reliably everywhere, so that's used instead of
        the widget/symbol-based rendering."""
        self.ensure_one()
        currency = self.company_id.currency_id
        code = ASCII_CURRENCY_LABELS.get(currency.name, currency.name or '')
        formatted = '{:,.2f}'.format(amount or 0.0)
        return '%s %s' % (code, formatted)

    def get_amount_in_words(self):
        """Return the Net Salary as words (Indian numbering system),
        e.g. 152744.5 -> 'One Lakh Fifty Two Thousand Seven Hundred
        Forty Four'."""
        self.ensure_one()
        amount = int(round(self.get_salary_line_total('NET')))
        try:
            from num2words import num2words
            words = num2words(amount, lang='en_IN')
        except Exception:
            return str(amount)
        return words.replace(',', '').replace(' and ', ' ').title()

    @api.onchange('date_from')
    def onchange_date_from(self):
        """Function for getting contract for employee"""
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # # computation of the salary input
        contracts = self.env['hr.version'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        if self.line_ids.search([('name', '=', 'Meal Voucher')]):
            self.line_ids.search(
                [('name', '=', 'Meal Voucher')]).salary_rule_id.write(
                {'quantity': self.worked_days_line_ids.number_of_days})
        return

    @api.onchange('date_to')
    def onchange_date_to(self):
        """Function for getting contract for employee"""
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # computation of the salary input
        contracts = self.env['hr.version'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        if self.line_ids.search([('name', '=', 'Meal Voucher')]):
            self.line_ids.search(
                [('name', '=', 'Meal Voucher')]).salary_rule_id.write(
                {'quantity': self.worked_days_line_ids.number_of_days})
        return
