from odoo import models, fields, api


class HrAttritionAssessment(models.Model):
    _name = 'hr.attrition.assessment'
    _description = 'HR Employee Retention Assessment'
    _order = 'assessment_date desc, id desc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    assessed_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    assessment_date = fields.Datetime(default=fields.Datetime.now, readonly=True)

    # ---- Rating questions (1–5) -----------------------------------------
    q_engagement = fields.Integer(
        string='Employee Engagement',
        default=3,
        help='1 = Visibly disengaged  ·  3 = Average  ·  5 = Highly engaged',
    )
    q_salary_satisfaction = fields.Integer(
        string='Salary Satisfaction',
        default=3,
        help='1 = Actively complaining  ·  3 = Neutral  ·  5 = Very happy',
    )
    q_career_growth = fields.Integer(
        string='Career Growth Satisfaction',
        default=3,
        help='1 = Feels stuck  ·  3 = Some progress  ·  5 = Clear growth path',
    )
    q_manager_relation = fields.Integer(
        string='Relationship with Manager',
        default=3,
        help='1 = Significant tension  ·  3 = Neutral  ·  5 = Strong bond',
    )
    q_retention_confidence = fields.Integer(
        string="HR's Retention Confidence",
        default=3,
        help='1 = Very likely to leave soon  ·  3 = Uncertain  ·  5 = Very likely to stay',
    )

    # ---- Yes / No questions ----------------------------------------------
    q_job_hunting = fields.Boolean(
        string='Signs of Job Hunting?',
        help='LinkedIn activity, unusual time-off, references requested, etc.',
    )
    q_recent_promotion = fields.Boolean(
        string='Promotion or Raise in Last 12 Months?',
    )
    q_burnout_risk = fields.Boolean(
        string='Workload / Burnout Concerns?',
        help='Employee has expressed fatigue, stress, or overload.',
    )

    # ---- HR notes --------------------------------------------------------
    notes = fields.Text(string='HR Notes (optional)')

    # ---- Derived risk score (stored, recomputed on save) ----------------
    assessment_risk_score = fields.Float(
        string='Assessment Risk Score',
        digits=(6, 1),
        help='0–100 risk score derived purely from HR answers.',
    )

    @api.depends(
        'q_engagement', 'q_salary_satisfaction', 'q_career_growth',
        'q_manager_relation', 'q_retention_confidence',
        'q_job_hunting', 'q_recent_promotion', 'q_burnout_risk',
    )
    def _compute_assessment_score(self):
        for rec in self:
            score = 50.0
            score -= (rec.q_engagement - 3) * 8.0
            score -= (rec.q_salary_satisfaction - 3) * 5.0
            score -= (rec.q_career_growth - 3) * 5.0
            score -= (rec.q_manager_relation - 3) * 3.0
            score -= (rec.q_retention_confidence - 3) * 10.0
            if rec.q_job_hunting:
                score += 25.0
            if rec.q_recent_promotion:
                score -= 15.0
            if rec.q_burnout_risk:
                score += 10.0
            rec.assessment_risk_score = max(0.0, min(100.0, round(score, 1)))

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._compute_assessment_score()
        rec.assessment_risk_score = rec.assessment_risk_score
        return rec
