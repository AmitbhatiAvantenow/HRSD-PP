from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

EDITABLE_STATES = ('draft', 'returned')


class HrTimesheetSheet(models.Model):
    _name = 'hr.timesheet.sheet'
    _description = 'Weekly Timesheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    active = fields.Boolean(default=True)

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, tracking=True,
        default=lambda self: self.env.user.employee_id)
    user_id = fields.Many2one(related='employee_id.user_id', string='User', store=True, readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Department', store=True, readonly=True)
    job_title = fields.Char(related='employee_id.job_title', string='Job Title', readonly=True)
    avatar_128 = fields.Image(related='employee_id.avatar_128', readonly=True)

    project_id = fields.Many2one('project.project', string='Project', tracking=True)

    date_start = fields.Date(string='Week Start', required=True, default=lambda self: self._default_week_start(), tracking=True)
    date_end = fields.Date(string='Week End', required=True, default=lambda self: self._default_week_start() + timedelta(days=6))
    week_number = fields.Char(string='Week', compute='_compute_week_number', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('returned', 'Returned'),
    ], default='draft', string='Status', tracking=True, copy=False)

    line_ids = fields.One2many('hr.timesheet.line', 'sheet_id', string='Timesheet Efforts', copy=True)

    total_hours = fields.Float(string='Total Hours', compute='_compute_totals', store=True)
    billable_hours = fields.Float(string='Billable Hours', compute='_compute_totals', store=True)
    non_billable_hours = fields.Float(string='Non-Billable Hours', compute='_compute_totals', store=True)
    overtime_hours = fields.Float(string='Overtime Hours', compute='_compute_totals', store=True)
    billable_percent = fields.Float(string='Billable %', compute='_compute_totals', store=True)
    progress_percent = fields.Float(string='Progress %', compute='_compute_totals', store=True)

    target_hours = fields.Float(related='company_id.timesheet_pro_weekly_target_hours', string='Target Hours', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    comments = fields.Text(string='Comments')
    manager_comment = fields.Text(string='Manager Comment', copy=False)
    submitted_date = fields.Datetime(string='Submitted On', readonly=True, copy=False)
    approved_date = fields.Datetime(string='Approved On', readonly=True, copy=False)
    approver_id = fields.Many2one('res.users', string='Reviewed By', readonly=True, copy=False)

    @api.model
    def _default_week_start(self):
        today = fields.Date.context_today(self)
        return today - timedelta(days=today.weekday())

    @api.depends('date_start')
    def _compute_week_number(self):
        for rec in self:
            if rec.date_start:
                iso = rec.date_start.isocalendar()
                rec.week_number = _('Week %s, %s') % (iso[1], iso[0])
            else:
                rec.week_number = False

    @api.depends('line_ids.hours', 'line_ids.billable', 'target_hours')
    def _compute_totals(self):
        for rec in self:
            total = sum(rec.line_ids.mapped('hours'))
            billable = sum(rec.line_ids.filtered('billable').mapped('hours'))
            rec.total_hours = total
            rec.billable_hours = billable
            rec.non_billable_hours = total - billable
            rec.overtime_hours = max(0.0, total - rec.target_hours)
            rec.billable_percent = (billable / total * 100) if total else 0.0
            rec.progress_percent = (total / rec.target_hours * 100) if rec.target_hours else 0.0

    @api.model
    def _build_week_lines(self, date_start):
        lines = []
        for i in range(7):
            day = date_start + timedelta(days=i)
            is_weekend = day.weekday() >= 5
            lines.append({
                'date': day,
                'start_time': 9.0,
                'end_time': 0.0 if is_weekend else 17.0,
                'hours': 0.0 if is_weekend else 8.0,
                'billable': not is_weekend,
            })
        return lines

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if not self.date_start:
            return
        self.date_end = self.date_start + timedelta(days=6)
        if not self.line_ids:
            self.line_ids = [(0, 0, vals) for vals in self._build_week_lines(self.date_start)]
        else:
            for line in self.line_ids:
                if line.date:
                    line.date = self.date_start + timedelta(days=line.date.weekday())

    @api.onchange('date_start', 'employee_id')
    def _onchange_warn_existing_week(self):
        if not (self.date_start and self.employee_id):
            return
        existing = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '=', self.date_start),
            ('id', '!=', self._origin.id),
        ], limit=1)
        if existing:
            return {
                'warning': {
                    'title': _('Timesheet Already Filled'),
                    'message': _(
                        'You have already filled the timesheet for this week (%(name)s). '
                        'No need to fill it again.'
                    ) % {'name': existing.name},
                }
            }

    @api.constrains('date_start')
    def _check_date_start_is_monday(self):
        for rec in self:
            if rec.date_start and rec.date_start.weekday() != 0:
                raise ValidationError(_(
                    "The week's Select Date must be a Monday, since a weekly timesheet "
                    "always runs Monday through Sunday."
                ))

    @api.constrains('employee_id', 'date_start')
    def _check_no_duplicate_week(self):
        for rec in self:
            if not (rec.employee_id and rec.date_start):
                continue
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('date_start', '=', rec.date_start),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'A timesheet for this week already exists for %(employee)s (%(name)s). '
                    'No need to fill it again.'
                ) % {'employee': rec.employee_id.name, 'name': duplicate.name})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.timesheet.sheet') or _('New')
        return super().create(vals_list)

    def _check_editable(self):
        for rec in self:
            if rec.state not in EDITABLE_STATES and not self.env.user.has_group('hr_timesheet_pro.group_timesheet_pro_manager'):
                raise AccessError(_('This timesheet is locked for editing in its current status.'))

    def write(self, vals):
        state_only = set(vals.keys()) <= {'state', 'submitted_date', 'approved_date', 'approver_id', 'manager_comment'}
        if not state_only and not self.env.user.has_group('hr_timesheet_pro.group_timesheet_pro_manager'):
            self._check_editable()
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft' and not self.env.user.has_group('hr_timesheet_pro.group_timesheet_pro_manager'):
                raise AccessError(_('Only draft timesheets can be deleted.'))
        return super().unlink()

    def action_submit(self):
        for rec in self:
            if rec.state not in EDITABLE_STATES:
                raise UserError(_('Only draft or returned timesheets can be submitted.'))
            if not rec.line_ids or not rec.total_hours:
                raise UserError(_('Please log at least some hours before submitting.'))
            missing_comments = rec.line_ids.filtered(
                lambda line: line.billable and line.hours and not (line.comments and line.comments.strip())
            )
            if missing_comments:
                raise UserError(_(
                    'Comments are mandatory for billable days. Please fill in comments for: %s'
                ) % ', '.join(missing_comments.mapped('day_name')))
            rec.write({
                'state': 'submitted',
                'submitted_date': fields.Datetime.now(),
                'manager_comment': False,
            })

    def _check_hr(self):
        if not self.env.user.has_group('hr_timesheet_pro.group_timesheet_pro_manager'):
            raise AccessError(_('Only Managers can review timesheets.'))

    def action_approve(self):
        self._check_hr()
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted timesheets can be approved.'))
        self.write({
            'state': 'approved',
            'approved_date': fields.Datetime.now(),
            'approver_id': self.env.user.id,
        })

    def action_reject(self, comment=None):
        self._check_hr()
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted timesheets can be rejected.'))
        self.write({
            'state': 'rejected',
            'approver_id': self.env.user.id,
            'manager_comment': comment or self.manager_comment,
        })

    def action_return(self, comment=None):
        self._check_hr()
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted timesheets can be returned.'))
        self.write({
            'state': 'returned',
            'approver_id': self.env.user.id,
            'manager_comment': comment or self.manager_comment,
        })

    def action_reset_draft(self):
        for rec in self:
            if rec.state not in ('rejected', 'returned') and not self.env.user.has_group('hr_timesheet_pro.group_timesheet_pro_manager'):
                raise UserError(_('Only rejected or returned timesheets can be reset to draft.'))
        self.write({'state': 'draft', 'approver_id': False, 'approved_date': False})

    def action_copy_last_week(self):
        self.ensure_one()
        previous = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '=', self.date_start - timedelta(days=7)),
        ], limit=1)
        if not previous:
            raise UserError(_('No timesheet found for the previous week.'))
        self.line_ids.unlink()
        for line in previous.line_ids:
            self.env['hr.timesheet.line'].create({
                'sheet_id': self.id,
                'date': line.date + timedelta(days=7),
                'start_time': line.start_time,
                'end_time': line.end_time,
                'hours': line.hours,
                'comments': line.comments,
                'billable': line.billable,
            })
        if not self.project_id:
            self.project_id = previous.project_id

    @api.model
    def action_open_current_week(self):
        employee = self.env.user.employee_id
        if not employee:
            raise UserError(_('No employee record is linked to your user account.'))
        week_start = self._default_week_start()
        sheet = self.search([
            ('employee_id', '=', employee.id),
            ('date_start', '=', week_start),
        ], limit=1)
        if not sheet:
            sheet = self.create({
                'employee_id': employee.id,
                'date_start': week_start,
                'line_ids': [(0, 0, vals) for vals in self._build_week_lines(week_start)],
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Weekly Timesheet'),
            'res_model': 'hr.timesheet.sheet',
            'view_mode': 'form',
            'views': [(self.env.ref('hr_timesheet_pro.view_hr_timesheet_sheet_form').id, 'form')],
            'res_id': sheet.id,
            'target': 'current',
        }
