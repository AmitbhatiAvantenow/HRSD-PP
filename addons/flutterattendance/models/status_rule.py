from odoo import fields, models


class FlutterAttendanceStatusRule(models.Model):
    _name = 'flutterattendance.status.rule'
    _description = 'Attendance Status Rule'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(
        required=True,
        help="Label shown on the attendance record's Status field, e.g. 'Half Day' or 'Absent'.",
    )
    code = fields.Char(
        required=True,
        help="Technical value stored on the record. Reuse 'present'/'half_day'/'absent' to stay "
             "compatible with the mobile app and existing filters, or make up a new one to add a "
             "brand new status (e.g. 'late', 'overtime'). Multiple rules may share the same code "
             "(e.g. two different reasons that both land on 'absent') as long as they also share "
             "the same name — the Status field's options are built from (code, name) pairs, and "
             "mismatched names for one code produce a broken duplicate-valued selection.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    condition = fields.Selection([
        ('missed_checkout', 'Check-out was never recorded (auto-closed by the next-day sweep)'),
        ('shift_half_day', "Worked less than the employee's shift Half-Day hours"),
        ('hours_range', 'Worked hours are between'),
        ('late', 'Checked in later than the shift start + grace period'),
        ('always', 'Always (use as the fallback/default rule)'),
    ], default='hours_range', required=True,
        help="Rules are evaluated in Sequence order; the first one that matches a record wins.")

    min_hours = fields.Float(string='Min Worked Hours', help="Rule applies when worked hours >= this value.")
    max_hours = fields.Float(
        string='Max Worked Hours',
        help="Rule applies when worked hours are strictly below this value. Leave at 0 for no upper bound.",
    )
    require_checkout = fields.Boolean(
        default=True,
        help="Only consider this rule for records that already have a check-out time. Untick for rules "
             "that should also apply to still-open (not yet checked-out) attendance.",
    )

    _sql_constraints = [
        ('code_not_empty', "CHECK (code != '')", 'The status code cannot be empty.'),
    ]
