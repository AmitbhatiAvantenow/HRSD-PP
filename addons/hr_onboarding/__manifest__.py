{
    'name': 'HR Onboarding',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Modern new-hire onboarding workspace: pipeline, journey, documents, tasks, equipment',
    'description': """
HR Onboarding
=============
A premium onboarding workspace for new hires:

* New Hire Pipeline - horizontal stage board with drag & drop
* Employee Journey - split-view profile / timeline / quick actions
* Documents workspace with upload & verification status
* Tasks & Checklists per onboarding
* Equipment tracking
* Automated stage-change emails
""",
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_onboarding_sequence.xml',
        'data/hr_onboarding_stage_data.xml',
        'data/hr_onboarding_mail_template_data.xml',
        'views/hr_onboarding_stage_views.xml',
        'views/hr_onboarding_task_views.xml',
        'views/hr_onboarding_document_views.xml',
        'views/hr_onboarding_equipment_views.xml',
        'views/hr_onboarding_views.xml',
        'views/hr_onboarding_menus.xml',
        'views/templates_document_portal.xml',
    ],
    'demo': [
        'demo/hr_onboarding_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_onboarding/static/src/scss/variables/hr_onboarding_variables.scss',
            'hr_onboarding/static/src/scss/*.scss',
            'hr_onboarding/static/src/dashboard/*.scss',
            'hr_onboarding/static/src/pipeline/*.scss',
            'hr_onboarding/static/src/journey/*.scss',
            'hr_onboarding/static/src/**/*.js',
            'hr_onboarding/static/src/**/*.xml',
            ('remove', 'hr_onboarding/static/src/js/document_portal.js'),
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
