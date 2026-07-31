# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrCase(models.Model):
    """An HR Case raised by/for an employee: a complaint or service request
    routed through Division/Category/Subcategory to an Assignment Group,
    tracked against an SLA, with optional manager approval and chatter."""
    _name = 'hr.case'
    _description = 'HR Case'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_opened desc, id desc'
    _rec_name = 'name'

    # ---------------------------------------------------------------
    # Identification
    # ---------------------------------------------------------------
    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                        default=lambda self: _('New'))

    employee_id = fields.Many2one(
        'hr.employee', string='Opened For', required=True, tracking=True,
        default=lambda self: self.env.user.employee_id,
        help='The employee this case is opened for. Defaults to the employee linked to the '
             'logged in user, so a self-service portal/employee always raises a case against '
             'their own hr.employee record.')
    subject_person_id = fields.Many2one(
        'hr.employee', string='Subject Person', tracking=True,
        help='Use this when the case concerns someone other than the requester '
             '(e.g. a complaint filed on behalf of, or about, a colleague).')

    # ---------------------------------------------------------------
    # Classification / routing catalog
    # ---------------------------------------------------------------
    service_id = fields.Many2one('hr.case.service', string='HR Service', required=True, tracking=True)
    division_id = fields.Many2one('hr.case.division', string='Division', required=True, tracking=True)
    category_id = fields.Many2one(
        'hr.case.category', string='Category', required=True, tracking=True,
        domain="[('division_id', '=', division_id)]")
    subcategory_id = fields.Many2one(
        'hr.case.subcategory', string='Subcategory',
        domain="[('category_id', '=', category_id)]")

    # ---------------------------------------------------------------
    # State / priority / source
    # ---------------------------------------------------------------
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'Work in Progress'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('closed_complete', 'Closed Complete'),
        ('closed_incomplete', 'Closed Incomplete'),
        ('cancelled', 'Cancelled'),
    ], default='new', required=True, tracking=True, copy=False)

    priority = fields.Selection([
        ('1', '1 - Critical'),
        ('2', '2 - High'),
        ('3', '3 - Moderate'),
        ('4', '4 - Low'),
        ('5', '5 - Planning'),
    ], default='3', required=True, tracking=True)

    source = fields.Selection([
        ('self_service', 'Self Service'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('walk_in', 'Walk-in'),
        ('manager', 'Manager Request'),
    ], default='self_service', required=True, string='Source')

    # ---------------------------------------------------------------
    # Dates
    # ---------------------------------------------------------------
    date_opened = fields.Datetime(string='Opened', default=fields.Datetime.now, readonly=True)
    due_date = fields.Datetime(string='Due Date')
    date_closed = fields.Datetime(string='Closed On', readonly=True, copy=False)
    opened_by_id = fields.Many2one('res.users', string='Opened By',
                                    default=lambda self: self.env.user, readonly=True)

    # ---------------------------------------------------------------
    # Assignment
    # ---------------------------------------------------------------
    team_id = fields.Many2one('hr.case.team', string='Assignment Group', tracking=True)
    team_member_ids = fields.Many2many('res.users', compute='_compute_team_member_ids',
                                        string='Group Members')
    user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    collaborator_ids = fields.Many2many(
        'res.users', 'hr_case_collaborator_rel', 'case_id', 'user_id', string='Collaborators')
    watcher_ids = fields.Many2many(
        'res.users', 'hr_case_watcher_rel', 'case_id', 'user_id', string='Watch List',
        help='Users added here are also subscribed as followers so they receive chatter '
             'notifications for this case.')

    # ---------------------------------------------------------------
    # Description
    # ---------------------------------------------------------------
    short_description = fields.Char(string='Short Description', required=True)
    description = fields.Html(string='Description / Fulfillment Instructions')

    # ---------------------------------------------------------------
    # SLA
    # ---------------------------------------------------------------
    sla_id = fields.Many2one('hr.case.sla', string='SLA Policy', compute='_compute_sla_id',
                              store=True, readonly=False,
                              help='Auto-suggested from Category + Priority, can be overridden.')
    will_escalate_on = fields.Datetime(string='Will Escalate On', compute='_compute_will_escalate_on',
                                        store=True)
    sla_breached = fields.Boolean(string='SLA Breached', default=False, copy=False, tracking=True)
    escalation_counter = fields.Integer(string='Escalation Counter', default=0, copy=False, readonly=True)

    # ---------------------------------------------------------------
    # Approval workflow (optional - only used if a case needs sign-off,
    # e.g. a payroll correction above a threshold)
    # ---------------------------------------------------------------
    approval_state = fields.Selection([
        ('no', 'No Approval Needed'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], default='no', string='Approval Status', tracking=True, copy=False)
    approver_id = fields.Many2one('res.users', string='Approver', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    # ---------------------------------------------------------------
    # Computes
    # ---------------------------------------------------------------
    @api.depends('team_id.member_ids')
    def _compute_team_member_ids(self):
        for case in self:
            case.team_member_ids = case.team_id.member_ids

    @api.depends('category_id', 'priority')
    def _compute_sla_id(self):
        Sla = self.env['hr.case.sla']
        for case in self:
            sla = False
            if case.category_id and case.priority:
                sla = Sla.search([
                    ('category_id', '=', case.category_id.id),
                    ('priority', '=', case.priority),
                ], limit=1)
            if not sla and case.priority:
                sla = Sla.search([
                    ('category_id', '=', False),
                    ('priority', '=', case.priority),
                ], limit=1)
            case.sla_id = sla

    @api.depends('sla_id', 'date_opened')
    def _compute_will_escalate_on(self):
        for case in self:
            if case.sla_id and case.date_opened:
                case.will_escalate_on = case.date_opened + timedelta(hours=case.sla_id.escalation_hours)
            else:
                case.will_escalate_on = False

    # ---------------------------------------------------------------
    # Onchange helpers
    # ---------------------------------------------------------------
    @api.onchange('service_id')
    def _onchange_service_id(self):
        for case in self:
            if case.service_id:
                case.division_id = case.service_id.division_id
                case.category_id = case.service_id.category_id
                case.subcategory_id = case.service_id.subcategory_id

    @api.onchange('watcher_ids')
    def _onchange_watcher_ids(self):
        for case in self:
            case.message_subscribe(partner_ids=case.watcher_ids.partner_id.ids)

    # ---------------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.case') or _('New')
        cases = super().create(vals_list)
        cases._send_notification('hr_case_management.mail_template_hr_case_created')
        return cases

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') in ('closed_complete', 'closed_incomplete'):
            self.write({'date_closed': fields.Datetime.now()})
        if vals.get('user_id'):
            self._send_notification('hr_case_management.mail_template_hr_case_assigned')
        return res

    # ---------------------------------------------------------------
    # Notifications
    # ---------------------------------------------------------------
    def _send_notification(self, template_xmlid):
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return
        for case in self:
            template.send_mail(case.id, force_send=False)

    # ---------------------------------------------------------------
    # Buttons / actions
    # ---------------------------------------------------------------
    def action_update(self):
        """Generic 'Update' button - simply saves; kept as an explicit
        action so it can be extended (e.g. trigger custom validations)."""
        return True

    def action_start_progress(self):
        self.write({'state': 'in_progress'})

    def action_close_complete(self):
        self.write({'state': 'closed_complete'})

    def action_close_incomplete(self):
        self.write({'state': 'closed_incomplete'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_submit_for_approval(self):
        for case in self:
            if not case.approver_id:
                raise UserError(_('Please set an Approver before submitting this case for approval.'))
            case.approval_state = 'to_approve'
            case.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Approval Required: %s', case.name),
                user_id=case.approver_id.id,
            )

    def action_approve(self):
        for case in self:
            case.approval_state = 'approved'
            case.message_post(body=_('Case approved by %s.', self.env.user.name))

    def action_refuse(self):
        for case in self:
            case.approval_state = 'refused'
            case.message_post(body=_('Case refused by %s.', self.env.user.name))

    # ---------------------------------------------------------------
    # SLA escalation (called by ir.cron, see data/hr_case_cron.xml)
    # ---------------------------------------------------------------
    def _cron_check_sla(self):
        now = fields.Datetime.now()
        overdue = self.search([
            ('will_escalate_on', '<=', now),
            ('sla_breached', '=', False),
            ('state', 'not in', ['closed_complete', 'closed_incomplete', 'cancelled']),
        ])
        for case in overdue:
            case.escalation_counter += 1
            case.sla_breached = True
            case.message_post(body=_('SLA breached: case escalated (escalation #%s).',
                                      case.escalation_counter))
            case._send_notification('hr_case_management.mail_template_hr_case_sla_breach')
