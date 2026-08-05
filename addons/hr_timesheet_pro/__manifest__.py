{
    'name': 'HR Timesheet Pro',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Modern enterprise timesheet & worklog workspace',
    'description': """
HR Timesheet Pro
=================
A premium timesheet management workspace:

* Workspace Dashboard - hero KPIs, weekly progress, pending approvals
* Weekly Timesheet - modern day-by-day effort grid
* My Timesheets / Team Timesheets
* Approvals board (Draft -> Submitted -> Approved / Rejected / Returned)
* Calendar view of submitted timesheets
* Role-based: Employees manage their own; HR/Admin has full access & approval rights
""",
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail', 'hr', 'project'],
    'data': [
        'security/hr_timesheet_pro_groups.xml',
        'security/ir.model.access.csv',
        'security/hr_timesheet_pro_security.xml',
        'data/hr_timesheet_pro_sequence.xml',
        'views/hr_timesheet_sheet_views.xml',
        'views/hr_employee_views.xml',
        'views/res_company_views.xml',
        'views/hr_timesheet_pro_menus.xml',
    ],
    'demo': [
        'demo/hr_timesheet_pro_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_timesheet_pro/static/src/scss/variables/hr_timesheet_pro_variables.scss',
            'hr_timesheet_pro/static/src/scss/*.scss',
            'hr_timesheet_pro/static/src/dashboard/*.scss',
            'hr_timesheet_pro/static/src/dashboard/*.js',
            'hr_timesheet_pro/static/src/dashboard/*.xml',
            'hr_timesheet_pro/static/src/navbar/*.scss',
            'hr_timesheet_pro/static/src/navbar/*.js',
            'hr_timesheet_pro/static/src/navbar/*.xml',
            'hr_timesheet_pro/static/src/fields/*.js',
            'hr_timesheet_pro/static/src/wizard/*.scss',
            'hr_timesheet_pro/static/src/wizard/*.js',
            'hr_timesheet_pro/static/src/wizard/*.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'post_init_hook': '_grant_timesheet_pro_groups',
}
