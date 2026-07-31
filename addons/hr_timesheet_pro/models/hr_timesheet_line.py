from odoo import api, fields, models


class HrTimesheetLine(models.Model):
    _name = 'hr.timesheet.line'
    _description = 'Timesheet Daily Effort'
    _order = 'date'

    sheet_id = fields.Many2one('hr.timesheet.sheet', string='Timesheet', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='sheet_id.employee_id', string='Employee', store=True, readonly=True)
    state = fields.Selection(related='sheet_id.state', string='Status', store=True, readonly=True)

    date = fields.Date(string='Date', required=True)
    day_name = fields.Char(string='Day', compute='_compute_day_name')

    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    hours = fields.Float(string='Hours')

    task_id = fields.Many2one('project.task', string='Task')
    comments = fields.Char(string='Comments')
    billable = fields.Boolean(string='Billable', default=True)

    @api.depends('date')
    def _compute_day_name(self):
        for rec in self:
            rec.day_name = rec.date.strftime('%A') if rec.date else ''
