from odoo import fields, models


class FlutterAttendanceLocation(models.Model):
    _name = 'flutterattendance.location'
    _description = 'Mobile Attendance Geofence Location'
    _order = 'is_primary desc, name'

    name = fields.Char(required=True)
    address = fields.Char()
    latitude = fields.Float(required=True, digits=(10, 7))
    longitude = fields.Float(required=True, digits=(10, 7))
    radius = fields.Integer(string='Radius (meters)', required=True, default=100)
    active = fields.Boolean(default=True)

    # The fallback location used for any employee not listed in
    # employee_ids below. Exactly one primary location should exist;
    # admins are expected to keep it that way (not DB-enforced, since a
    # brand-new install has zero locations and that's a valid state too).
    is_primary = fields.Boolean(
        string='Primary',
        help="Fallback location for employees with no specific assignment below.",
    )

    # Empty = this location doesn't target anyone specifically (only
    # meaningful for the primary/fallback location). Non-empty = this
    # location's geofence applies only to these employees.
    employee_ids = fields.Many2many(
        'hr.employee', 'flutterattendance_location_employee_rel',
        'location_id', 'employee_id',
        string='Assigned Employees',
    )

    def resolve_for_employee(self, employee):
        """The single location that should govern this employee's geofence:
        one that specifically lists them, falling back to the primary/
        catch-all location, or an empty recordset if nothing is configured
        at all (geofence check is then skipped entirely, as before)."""
        specific = self.search([('employee_ids', 'in', employee.id)], limit=1)
        if specific:
            return specific
        return self.search([('is_primary', '=', True), ('employee_ids', '=', False)], limit=1)
