import uuid
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrOnboarding(models.Model):
    _name = 'hr.onboarding'
    _description = 'Employee Onboarding'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, joining_date, id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    active = fields.Boolean(default=True)

    first_name = fields.Char(required=True, tracking=True)
    last_name = fields.Char(tracking=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    email = fields.Char(string='Email Address')
    phone = fields.Char()
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    image_1920 = fields.Image(string='Photo', max_width=1920, max_height=1920)

    employee_id = fields.Many2one('hr.employee', string='Employee Record', tracking=True,
                                   help='Linked once the new hire is converted into a full employee record.')
    job_id = fields.Many2one('hr.job', string='Job Position', tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    manager_id = fields.Many2one('hr.employee', string='Reporting Manager', tracking=True)
    buddy_id = fields.Many2one('hr.employee', string='Onboarding Buddy', tracking=True)
    hr_user_id = fields.Many2one(
        'res.users', string='Assigned HR', tracking=True,
        default=lambda self: self.env.user)

    joining_date = fields.Date(string='Joining Date', tracking=True, required=True)
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
        'hr.onboarding.stage', string='Stage', tracking=True, group_expand='_read_group_stage_ids',
        default=lambda self: self.env['hr.onboarding.stage'].search([], order='sequence', limit=1),
        ondelete='restrict')
    color = fields.Integer(related='stage_id.color', string='Color')

    task_ids = fields.One2many('hr.onboarding.task', 'onboarding_id', string='Tasks')
    document_ids = fields.One2many('hr.onboarding.document', 'onboarding_id', string='Documents')
    equipment_ids = fields.One2many('hr.onboarding.equipment', 'onboarding_id', string='Equipment')
    stage_log_ids = fields.One2many('hr.onboarding.stage.log', 'onboarding_id', string='Stage History')

    task_count = fields.Integer(compute='_compute_counts')
    task_done_count = fields.Integer(compute='_compute_counts')
    document_count = fields.Integer(compute='_compute_counts')
    missing_document_count = fields.Integer(compute='_compute_counts')
    equipment_count = fields.Integer(compute='_compute_counts')
    equipment_pending_count = fields.Integer(compute='_compute_counts')

    progress = fields.Integer(string='Progress %', compute='_compute_progress', store=True)
    countdown = fields.Char(string='Countdown', compute='_compute_countdown', store=True)
    is_delayed = fields.Boolean(string='Delayed', compute='_compute_countdown', store=True)

    notes = fields.Text()

    access_token = fields.Char(
        string='Portal Access Token', copy=False, readonly=True,
        default=lambda self: uuid.uuid4().hex)
    portal_document_url = fields.Char(
        string='Document Submission Link', compute='_compute_portal_document_url')
    declaration_signed = fields.Boolean(string='Declaration Signed', readonly=True)
    declaration_date = fields.Datetime(string='Declaration Signed On', readonly=True)

    def _compute_portal_document_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.portal_document_url = f'{base_url}/onboarding/documents/{rec.access_token}'

    @api.depends('first_name', 'last_name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = ' '.join(p for p in (rec.first_name, rec.last_name) if p)

    @api.depends('task_ids.done', 'document_ids.status', 'equipment_ids.status')
    def _compute_counts(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)
            rec.task_done_count = len(rec.task_ids.filtered('done'))
            rec.document_count = len(rec.document_ids)
            rec.missing_document_count = len(
                rec.document_ids.filtered(lambda d: d.status in ('pending', 'rejected')))
            rec.equipment_count = len(rec.equipment_ids)
            rec.equipment_pending_count = len(
                rec.equipment_ids.filtered(lambda e: e.status == 'pending'))

    @api.depends('stage_id')
    def _compute_progress(self):
        stages = self.env['hr.onboarding.stage'].search([], order='sequence')
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

    @api.depends('joining_date', 'stage_id.is_final')
    def _compute_countdown(self):
        today = date.today()
        for rec in self:
            rec.is_delayed = False
            if not rec.joining_date:
                rec.countdown = ''
                continue
            delta = (rec.joining_date - today).days
            if rec.stage_id.is_final:
                rec.countdown = _('Completed')
            elif delta > 0:
                rec.countdown = _('Joins in %s day(s)') % delta
            elif delta == 0:
                rec.countdown = _('Joining today')
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
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.onboarding') or _('New')
        records = super().create(vals_list)
        for rec in records:
            if rec.stage_id:
                self.env['hr.onboarding.stage.log'].create({
                    'onboarding_id': rec.id,
                    'stage_id': rec.stage_id.id,
                })
                rec._send_stage_email(rec.stage_id)
        return records

    def write(self, vals):
        stage_changed = 'stage_id' in vals
        result = super().write(vals)
        if stage_changed and vals.get('stage_id'):
            new_stage = self.env['hr.onboarding.stage'].browse(vals['stage_id'])
            for rec in self:
                self.env['hr.onboarding.stage.log'].create({
                    'onboarding_id': rec.id,
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
            'tag': 'hr_onboarding_journey',
            'name': _('Employee Journey - %s') % self.display_name,
            'params': {'onboarding_id': self.id},
        }

    def action_send_document_request(self):
        template = self.env.ref('hr_onboarding.mail_template_documents_pending', raise_if_not_found=False)
        for rec in self:
            if not rec.email:
                raise UserError(_('%s has no email address on file.') % rec.display_name)
            if not rec.access_token:
                rec.access_token = uuid.uuid4().hex
            if template:
                template.send_mail(rec.id, force_send=True)
                rec.message_post(body=_('Document submission link emailed to %s.') % rec.email)

    def action_move_next_stage(self):
        stages = self.env['hr.onboarding.stage'].search([], order='sequence')
        for rec in self:
            stage_list = list(stages)
            try:
                idx = stage_list.index(rec.stage_id)
            except ValueError:
                continue
            if idx + 1 < len(stage_list):
                rec.stage_id = stage_list[idx + 1].id
