{
    'name': 'HR Offboarding',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Modern employee offboarding workspace: exit pipeline, journey, clearance, assets, payroll',
    'description': """
HR Offboarding
==============
A premium offboarding workspace for departing employees:

* Exit Pipeline - horizontal stage board with drag & drop
* Employee Exit Journey - split-view profile / timeline / quick actions
* Clearance Center across departments (HR, Finance, IT, Admin, Security, Facilities, Legal, Manager)
* Asset return tracking
* Full & final payroll settlement
* Exit interviews
* Documents (experience letter, relieving letter, settlement letter, etc.)
* Automated stage-change emails
""",
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_offboarding_sequence.xml',
        'data/hr_offboarding_stage_data.xml',
        'data/hr_offboarding_mail_template_data.xml',
        'views/hr_offboarding_stage_views.xml',
        'views/hr_offboarding_task_views.xml',
        'views/hr_offboarding_clearance_views.xml',
        'views/hr_offboarding_asset_views.xml',
        'views/hr_offboarding_document_views.xml',
        'views/hr_offboarding_payroll_views.xml',
        'views/hr_offboarding_interview_views.xml',
        'views/hr_offboarding_request_views.xml',
        'views/hr_offboarding_menus.xml',
    ],
    'demo': [
        'demo/hr_offboarding_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_offboarding/static/src/scss/variables/hr_offboarding_variables.scss',
            'hr_offboarding/static/src/scss/*.scss',
            'hr_offboarding/static/src/dashboard/*.scss',
            'hr_offboarding/static/src/pipeline/*.scss',
            'hr_offboarding/static/src/journey/*.scss',
            'hr_offboarding/static/src/**/*.js',
            'hr_offboarding/static/src/**/*.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
