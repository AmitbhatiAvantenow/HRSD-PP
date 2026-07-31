from odoo import models, fields, api


STAGE_SELECTION = [
    ('to_do', 'To Do'),
    ('in_progress', 'In Progress'),
    ('in_review', 'In Review'),
    ('stuck', 'Stuck'),
    ('completed', 'Completed'),
]

PRIORITY_SELECTION = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

_SYNC_TRIGGER_FIELDS = {'employee_id', 'date', 'hours', 'name'}


class HrTask(models.Model):
    _name = 'hr.task'
    _description = 'Employee To-Do Task'
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Task', required=True)
    employee_id = fields.Many2one('hr.employee', string='Assignee', required=True, index=True, ondelete='cascade')
    stage = fields.Selection(STAGE_SELECTION, default='to_do', required=True)
    priority = fields.Selection(PRIORITY_SELECTION, default='medium', required=True)
    tag = fields.Char(string='Tag')
    description = fields.Text()
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    hours = fields.Float(string='Effort (Hours)')

    timesheet_entry_id = fields.Many2one('hr.timesheet.entry', string='Timesheet Entry', ondelete='set null', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        tasks._sync_timesheet()
        return tasks

    def write(self, vals):
        res = super().write(vals)
        if _SYNC_TRIGGER_FIELDS & set(vals):
            self._sync_timesheet()
        return res

    def unlink(self):
        entries = self.mapped('timesheet_entry_id')
        res = super().unlink()
        entries._recompute_from_tasks()
        return res

    def _sync_timesheet(self):
        Entry = self.env['hr.timesheet.entry']
        touched = self.env['hr.timesheet.entry']
        for task in self:
            if not task.employee_id or not task.date:
                continue
            entry = task.timesheet_entry_id
            if not entry or entry.employee_id != task.employee_id or entry.date != task.date:
                entry = Entry.search([
                    ('employee_id', '=', task.employee_id.id),
                    ('date', '=', task.date),
                ], limit=1)
                if not entry:
                    entry = Entry.create({
                        'employee_id': task.employee_id.id,
                        'date': task.date,
                    })
                old_entry = task.timesheet_entry_id
                task.timesheet_entry_id = entry.id
                touched |= old_entry
            touched |= entry
        touched._recompute_from_tasks()
