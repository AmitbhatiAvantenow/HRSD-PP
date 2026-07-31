from . import models


def _grant_timesheet_pro_groups(env):
    # Declarative writes to implied_ids on base.group_user / hr.group_hr_user
    # via XML data are not reliably picked up on module upgrade, so the
    # baseline Employee access (all internal users) and Manager access
    # (existing HR Officers) are granted imperatively here instead.
    base_group = env.ref('base.group_user')
    employee_group = env.ref('hr_timesheet_pro.group_timesheet_pro_employee')
    if employee_group not in base_group.implied_ids:
        base_group.write({'implied_ids': [(4, employee_group.id)]})

    hr_group = env.ref('hr.group_hr_user')
    manager_group = env.ref('hr_timesheet_pro.group_timesheet_pro_manager')
    if manager_group not in hr_group.implied_ids:
        hr_group.write({'implied_ids': [(4, manager_group.id)]})
