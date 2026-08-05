from odoo import _, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_open_timesheet_pro(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheet Pro'),
            'res_model': 'hr.timesheet.sheet',
            'view_mode': 'list,form,calendar',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
