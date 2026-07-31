from odoo import models, fields, api


class HrTimesheetEntry(models.Model):
    _name = 'hr.timesheet.entry'
    _description = 'Timesheet Entry'
    _order = 'date desc'
    _rec_name = 'code'

    code = fields.Char(string='Number', copy=False, readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee Name', required=True, index=True, ondelete='cascade')
    email = fields.Char(string='Email', related='employee_id.work_email', store=True, readonly=True)
    date = fields.Date(string='Date', required=True, index=True)
    day_name = fields.Char(string='Day', compute='_compute_day_name', store=True)
    start_time = fields.Float(string='Start Time', default=9.0)
    end_time = fields.Float(string='End Time', default=0.0)
    hours = fields.Float(string='Efforts in Hour')
    short_description = fields.Char(string='Short Description')
    comments = fields.Text(string='Comments')

    task_ids = fields.One2many('hr.task', 'timesheet_entry_id', string='Tasks')

    @api.depends('date')
    def _compute_day_name(self):
        for rec in self:
            rec.day_name = rec.date.strftime('%A') if rec.date else ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('hr.timesheet.entry') or 'New'
        return super().create(vals_list)

    def _recompute_from_tasks(self):
        for entry in self:
            tasks = entry.task_ids
            entry.hours = sum(tasks.mapped('hours'))
            entry.comments = '\n'.join(t.name for t in tasks if t.name)
            entry.short_description = tasks[0].name if tasks else ''
