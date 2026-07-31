from odoo import fields, models


class HrOffboardingClearance(models.Model):
    _name = 'hr.offboarding.clearance'
    _description = 'Offboarding Department Clearance'
    _order = 'id desc'

    name = fields.Char(compute='_compute_name', store=True)
    request_id = fields.Many2one('hr.offboarding.request', required=True, ondelete='cascade', index=True)
    department = fields.Selection([
        ('hr', 'HR'),
        ('finance', 'Finance'),
        ('it', 'IT'),
        ('administration', 'Administration'),
        ('security', 'Security'),
        ('facilities', 'Facilities'),
        ('legal', 'Legal'),
        ('manager', 'Manager'),
    ], required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('needs_action', 'Needs Action'),
    ], default='pending', required=True)
    approver_id = fields.Many2one('res.users', string='Approver')
    comments = fields.Text()
    signed_date = fields.Datetime(string='Signed On')

    _request_department_uniq = models.Constraint(
        'unique(request_id, department)',
        'Only one clearance row per department is allowed per exit request.',
    )

    def _compute_name(self):
        labels = dict(self._fields['department'].selection)
        for rec in self:
            rec.name = labels.get(rec.department, rec.department)

    def action_approve(self):
        self.write({'status': 'approved', 'approver_id': self.env.user.id, 'signed_date': fields.Datetime.now()})

    def action_reject(self):
        self.write({'status': 'rejected', 'approver_id': self.env.user.id, 'signed_date': fields.Datetime.now()})
