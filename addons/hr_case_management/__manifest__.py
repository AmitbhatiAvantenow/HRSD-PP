{
    'name': 'HR Case Management',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees raise HR cases (complaints / requests) with categories, SLA, '
               'assignment groups, approvals and email notifications',
    'description': """
HR Case Management
===================
Lets any employee raise an HR Case (complaint or service request) that references
the Employee model, similar to an HR Service Desk / Case form.

Features
--------
* Configurable Division / Category / Subcategory / HR Service catalog
* Assignment Groups (teams) with a Team Leader and Members
* SLA Policies per Category & Priority with automatic escalation tracking
* Optional approval workflow (Submit for Approval / Approve / Refuse)
* Automatic email notifications on creation, assignment and SLA breach
  (configurable mail templates + scheduled action)
* Full chatter (comments / internal work notes / activities / followers)
* Access rights for Employee / HR Officer / HR Manager`
""",
    'author': 'Your Company',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': ['hr', 'mail', 'portal', 'website'],
    'data': [
        'security/hr_case_security.xml',
        'security/ir.model.access.csv',
        'data/hr_case_sequence.xml',
        'data/hr_case_mail_templates.xml',
        'data/hr_case_cron.xml',
        'data/hr_case_demo_config.xml',
        'views/hr_case_config_views.xml',
        'views/hr_case_views.xml',
        'views/hr_case_producer_views.xml',
        'views/hr_case_catalog_views.xml',
        'views/hr_case_portal_templates.xml',
        'views/hr_case_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_case_management/static/src/xml/hr_service_form.xml',
            'hr_case_management/static/src/js/hr_service_form.js',
        ],
        'web.assets_frontend': [
            'hr_case_management/static/src/css/portal.css',
        ],
    },
    'installable': True,
    'application': True,
}
