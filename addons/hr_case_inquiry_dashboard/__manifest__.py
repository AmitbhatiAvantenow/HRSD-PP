# -*- coding: utf-8 -*-
{
    'name': 'Employee Services Inquiry Dashboard',
    'version': '19.0.1.0.0',
    'summary': 'Standalone public dashboard to submit Employee Service Inquiries as HR Cases',
    'description': """
Employee Services Inquiry Dashboard
====================================
Adds a standalone web page (no backend menu) where a logged-in employee can
submit an "Employee Services Inquiry". On submit, an hr.case record is
created behind the scenes and the page shows a confirmation that the
request has been submitted.

Built with an OWL widget (static/src/js, static/src/xml) and dedicated
CSS (static/src/css), rendered through a public web controller route.
""",
    'category': 'Human Resources',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'hr', 'hr_case_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_case_inquiry_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'hr_case_inquiry_dashboard/static/src/css/hr_case_inquiry_dashboard.css',
            'hr_case_inquiry_dashboard/static/src/xml/hr_case_inquiry_dashboard.xml',
            'hr_case_inquiry_dashboard/static/src/js/hr_case_inquiry_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
