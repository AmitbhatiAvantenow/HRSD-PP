from datetime import date

from odoo import models, fields, api


class HrAppraisal(models.Model):
    _name = 'hr.appraisal'
    _description = 'Employee Performance Appraisal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_end desc, id desc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='Department')
    job_id = fields.Many2one(related='employee_id.job_id', store=True, string='Job Position')
    manager_id = fields.Many2one('hr.employee', string='Reviewing Manager', tracking=True)

    cycle_type = fields.Selection([
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half-Yearly'),
        ('annual', 'Annual'),
        ('probation', 'Probation'),
        ('project', 'Project-Based'),
    ], default='annual', required=True, string='Review Cycle', tracking=True)

    period_start = fields.Date(string='Period Start', default=lambda self: date.today().replace(month=1, day=1))
    period_end = fields.Date(string='Period End', default=fields.Date.today)
    deadline_date = fields.Date(string='Deadline')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('self_assessment', 'Self-Assessment'),
        ('manager_review', 'Manager Review'),
        ('calibration', 'Calibration'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True)

    self_assessment_date = fields.Datetime(readonly=True)
    manager_review_date = fields.Datetime(readonly=True)
    completion_date = fields.Datetime(readonly=True)

    goal_ids = fields.One2many('hr.appraisal.goal', 'appraisal_id', string='Goals / OKRs', copy=True)
    competency_ids = fields.One2many('hr.appraisal.competency', 'appraisal_id', string='Competencies', copy=True)
    feedback_ids = fields.One2many('hr.appraisal.feedback', 'appraisal_id', string='360° Feedback')

    goal_count = fields.Integer(compute='_compute_counts')
    competency_count = fields.Integer(compute='_compute_counts')
    feedback_count = fields.Integer(compute='_compute_counts')

    self_goal_score = fields.Float(compute='_compute_scores', store=True, digits=(5, 1), string='Self Goal Score')
    manager_goal_score = fields.Float(compute='_compute_scores', store=True, digits=(5, 1), string='Manager Goal Score')
    self_competency_score = fields.Float(compute='_compute_scores', store=True, digits=(5, 1), string='Self Competency Score')
    manager_competency_score = fields.Float(compute='_compute_scores', store=True, digits=(5, 1), string='Manager Competency Score')
    peer_feedback_score = fields.Float(compute='_compute_scores', store=True, digits=(5, 1), string='360° Feedback Score')

    overall_self_score = fields.Float(compute='_compute_scores', store=True, digits=(5, 1))
    overall_manager_score = fields.Float(compute='_compute_scores', store=True, digits=(5, 1))
    overall_score = fields.Float(compute='_compute_scores', store=True, digits=(5, 1), string='Final Score')

    performance_band = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('exceeds', 'Exceeds Expectations'),
        ('meets', 'Meets Expectations'),
        ('below', 'Below Expectations'),
        ('unsatisfactory', 'Unsatisfactory'),
    ], compute='_compute_scores', store=True)

    potential = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], default='medium', string='Growth Potential', tracking=True)

    nine_box_label = fields.Char(compute='_compute_nine_box', store=True, string='9-Box Category')

    strengths = fields.Text()
    areas_of_improvement = fields.Text()
    development_plan = fields.Text()
    employee_comments = fields.Text()
    manager_comments = fields.Text()
    hr_comments = fields.Text()

    is_overdue = fields.Boolean(compute='_compute_is_overdue', store=True)

    _sql_constraints = [
        ('period_check', 'CHECK (period_end >= period_start)', 'The period end date must be after the start date.'),
    ]

    @api.depends('goal_ids', 'competency_ids', 'feedback_ids')
    def _compute_counts(self):
        for rec in self:
            rec.goal_count = len(rec.goal_ids)
            rec.competency_count = len(rec.competency_ids)
            rec.feedback_count = len(rec.feedback_ids)

    @api.depends(
        'goal_ids.weight', 'goal_ids.self_progress', 'goal_ids.manager_progress',
        'competency_ids.self_score', 'competency_ids.manager_score',
        'feedback_ids.rating', 'feedback_ids.relation', 'state',
    )
    def _compute_scores(self):
        for rec in self:
            goals = rec.goal_ids
            total_weight = sum(goals.mapped('weight'))
            if goals and total_weight:
                rec.self_goal_score = sum(g.weight * g.self_progress for g in goals) / total_weight
                rec.manager_goal_score = sum(g.weight * g.manager_progress for g in goals) / total_weight
            elif goals:
                rec.self_goal_score = sum(goals.mapped('self_progress')) / len(goals)
                rec.manager_goal_score = sum(goals.mapped('manager_progress')) / len(goals)
            else:
                rec.self_goal_score = 0.0
                rec.manager_goal_score = 0.0

            comps = rec.competency_ids
            if comps:
                rec.self_competency_score = sum(comps.mapped('self_score')) / len(comps) * 20.0
                rec.manager_competency_score = sum(comps.mapped('manager_score')) / len(comps) * 20.0
            else:
                rec.self_competency_score = 0.0
                rec.manager_competency_score = 0.0

            peers = rec.feedback_ids.filtered(lambda f: f.relation != 'self')
            rec.peer_feedback_score = (sum(peers.mapped('rating')) / len(peers) * 20.0) if peers else 0.0

            rec.overall_self_score = round(rec.self_goal_score * 0.6 + rec.self_competency_score * 0.4, 1)

            if rec.manager_goal_score or rec.manager_competency_score:
                manager_core = rec.manager_goal_score * 0.6 + rec.manager_competency_score * 0.4
                if rec.peer_feedback_score:
                    manager_core = manager_core * 0.85 + rec.peer_feedback_score * 0.15
                rec.overall_manager_score = round(manager_core, 1)
            else:
                rec.overall_manager_score = 0.0

            if rec.overall_manager_score:
                rec.overall_score = round(rec.overall_manager_score * 0.7 + rec.overall_self_score * 0.3, 1)
            else:
                rec.overall_score = rec.overall_self_score

            score = rec.overall_score
            if score >= 90:
                rec.performance_band = 'outstanding'
            elif score >= 75:
                rec.performance_band = 'exceeds'
            elif score >= 60:
                rec.performance_band = 'meets'
            elif score >= 40:
                rec.performance_band = 'below'
            else:
                rec.performance_band = 'unsatisfactory'

    @api.depends('performance_band', 'potential')
    def _compute_nine_box(self):
        band_map = {
            'outstanding': 'high', 'exceeds': 'high',
            'meets': 'medium',
            'below': 'low', 'unsatisfactory': 'low',
        }
        labels = {
            ('high', 'high'): 'Star',
            ('high', 'medium'): 'High Performer',
            ('high', 'low'): 'Solid Professional',
            ('medium', 'high'): 'High Potential',
            ('medium', 'medium'): 'Core Performer',
            ('medium', 'low'): 'Effective',
            ('low', 'high'): 'Rough Diamond',
            ('low', 'medium'): 'Inconsistent Performer',
            ('low', 'low'): 'Underperformer',
        }
        for rec in self:
            perf = band_map.get(rec.performance_band, 'medium')
            rec.nine_box_label = labels.get((perf, rec.potential or 'medium'), 'Core Performer')

    @api.depends('deadline_date', 'state')
    def _compute_is_overdue(self):
        today = date.today()
        for rec in self:
            rec.is_overdue = bool(
                rec.deadline_date and rec.deadline_date < today
                and rec.state not in ('completed', 'cancelled')
            )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id.parent_id:
                rec.manager_id = rec.employee_id.parent_id

    def action_start_self_assessment(self):
        self.write({'state': 'self_assessment'})
        self.message_post(body='Self-assessment stage started.')

    def action_submit_self_assessment(self):
        self.write({'state': 'manager_review', 'self_assessment_date': fields.Datetime.now()})
        self.message_post(body='Employee submitted their self-assessment.')

    def action_send_to_calibration(self):
        self.write({'state': 'calibration'})
        self.message_post(body='Sent to calibration.')

    def action_complete_manager_review(self):
        now = fields.Datetime.now()
        self.write({'state': 'completed', 'manager_review_date': now, 'completion_date': now})
        self.message_post(body='Manager review completed and appraisal finalized.')

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_open_appraisal_dashboard(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/hrsd/appraisal',
            'target': 'self',
        }
