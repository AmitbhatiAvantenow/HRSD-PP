from datetime import date

from odoo import api, fields, models, _


class HrOffboardingRequest(models.Model):
    _name = 'hr.offboarding.request'
    _description = 'Employee Offboarding Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, last_working_day, id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    active = fields.Boolean(default=True)

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    email = fields.Char(string='Email Address')
    job_id = fields.Many2one('hr.job', string='Job Position', tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    manager_id = fields.Many2one('hr.employee', string='Reporting Manager', tracking=True)
    successor_id = fields.Many2one('hr.employee', string='Successor', tracking=True)
    hr_user_id = fields.Many2one(
        'res.users', string='Assigned HR', tracking=True,
        default=lambda self: self.env.user)

    resignation_date = fields.Date(string='Resignation Date', tracking=True, default=fields.Date.today)
    last_working_day = fields.Date(string='Last Working Day', tracking=True, required=True)
    notice_period_days = fields.Integer(string='Notice Period (days)')
    reason = fields.Selection([
        ('better_opportunity', 'Better Opportunity'),
        ('compensation', 'Compensation'),
        ('relocation', 'Relocation'),
        ('higher_education', 'Higher Education'),
        ('health', 'Health / Personal'),
        ('performance', 'Performance / Involuntary'),
        ('other', 'Other'),
    ], string='Exit Reason', default='other')

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], default='1', string='Priority', tracking=True)
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked'),
    ], default='normal', string='Status', tracking=True)

    stage_id = fields.Many2one(
        'hr.offboarding.stage', string='Stage', tracking=True, group_expand='_read_group_stage_ids',
        default=lambda self: self.env['hr.offboarding.stage'].search([], order='sequence', limit=1),
        ondelete='restrict')
    color = fields.Integer(related='stage_id.color', string='Color')

    task_ids = fields.One2many('hr.offboarding.task', 'request_id', string='Tasks')
    asset_ids = fields.One2many('hr.offboarding.asset', 'request_id', string='Assets')
    clearance_ids = fields.One2many('hr.offboarding.clearance', 'request_id', string='Clearances')
    document_ids = fields.One2many('hr.offboarding.document', 'request_id', string='Documents')
    payroll_ids = fields.One2many('hr.offboarding.payroll', 'request_id', string='Settlement')
    interview_ids = fields.One2many('hr.offboarding.interview', 'request_id', string='Exit Interviews')
    stage_log_ids = fields.One2many('hr.offboarding.stage.log', 'request_id', string='Stage History')

    task_count = fields.Integer(compute='_compute_counts')
    task_done_count = fields.Integer(compute='_compute_counts')
    asset_count = fields.Integer(compute='_compute_counts')
    asset_pending_count = fields.Integer(compute='_compute_counts')
    clearance_count = fields.Integer(compute='_compute_counts')
    clearance_pending_count = fields.Integer(compute='_compute_counts')
    document_count = fields.Integer(compute='_compute_counts')
    missing_document_count = fields.Integer(compute='_compute_counts')

    progress = fields.Integer(string='Progress %', compute='_compute_progress', store=True)
    countdown = fields.Char(string='Countdown', compute='_compute_countdown', store=True)
    is_delayed = fields.Boolean(string='Delayed', compute='_compute_countdown', store=True)

    notes = fields.Text()

    @api.depends(
        'task_ids.done', 'asset_ids.status', 'clearance_ids.status', 'document_ids.status')
    def _compute_counts(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)
            rec.task_done_count = len(rec.task_ids.filtered('done'))
            rec.asset_count = len(rec.asset_ids)
            rec.asset_pending_count = len(rec.asset_ids.filtered(lambda a: a.status == 'pending'))
            rec.clearance_count = len(rec.clearance_ids)
            rec.clearance_pending_count = len(
                rec.clearance_ids.filtered(lambda c: c.status in ('pending', 'needs_action')))
            rec.document_count = len(rec.document_ids)
            rec.missing_document_count = len(
                rec.document_ids.filtered(lambda d: d.status in ('pending', 'rejected')))

    @api.depends('stage_id')
    def _compute_progress(self):
        stages = self.env['hr.offboarding.stage'].search([], order='sequence')
        total = len(stages) or 1
        index_by_id = {s.id: i for i, s in enumerate(stages)}
        for rec in self:
            if not rec.stage_id:
                rec.progress = 0
                continue
            if rec.stage_id.is_final:
                rec.progress = 100
                continue
            idx = index_by_id.get(rec.stage_id.id, 0)
            rec.progress = round((idx / total) * 100)

    @api.depends('last_working_day', 'stage_id.is_final')
    def _compute_countdown(self):
        today = date.today()
        for rec in self:
            rec.is_delayed = False
            if not rec.last_working_day:
                rec.countdown = ''
                continue
            delta = (rec.last_working_day - today).days
            if rec.stage_id.is_final:
                rec.countdown = _('Completed')
            elif delta > 0:
                rec.countdown = _('%s day(s) to LWD') % delta
            elif delta == 0:
                rec.countdown = _('Last working day today')
            else:
                rec.countdown = _('%s day(s) overdue') % abs(delta)
                rec.is_delayed = True

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return stages.search([], order='sequence')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.offboarding.request') or _('New')
        records = super().create(vals_list)
        for rec in records:
            if rec.stage_id:
                self.env['hr.offboarding.stage.log'].create({
                    'request_id': rec.id,
                    'stage_id': rec.stage_id.id,
                })
                rec._send_stage_email(rec.stage_id)
        return records

    def write(self, vals):
        stage_changed = 'stage_id' in vals
        result = super().write(vals)
        if stage_changed and vals.get('stage_id'):
            new_stage = self.env['hr.offboarding.stage'].browse(vals['stage_id'])
            for rec in self:
                self.env['hr.offboarding.stage.log'].create({
                    'request_id': rec.id,
                    'stage_id': new_stage.id,
                })
                rec._send_stage_email(new_stage)
        return result

    def _send_stage_email(self, stage):
        self.ensure_one()
        if stage.mail_template_id and self.email:
            stage.mail_template_id.send_mail(self.id, force_send=False)

    def action_open_journey(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hr_offboarding_journey',
            'name': _('Exit Journey - %s') % self.employee_id.name,
            'params': {'request_id': self.id},
        }

    def action_move_next_stage(self):
        stages = self.env['hr.offboarding.stage'].search([], order='sequence')
        for rec in self:
            stage_list = list(stages)
            try:
                idx = stage_list.index(rec.stage_id)
            except ValueError:
                continue
            if idx + 1 < len(stage_list):
                rec.stage_id = stage_list[idx + 1].id

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.job_id = rec.employee_id.job_id
                rec.department_id = rec.employee_id.department_id
                rec.manager_id = rec.employee_id.parent_id
                rec.email = rec.employee_id.work_email
