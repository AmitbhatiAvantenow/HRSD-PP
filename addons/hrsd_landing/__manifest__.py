# -*- coding: utf-8 -*-
{
    'name': 'HRSD Landing & Login Theme',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Modern animated landing page and rebranded login screen for HRSD Solution',
    'description': """
HRSD Landing & Login Theme
===========================
* Replaces the website homepage ("/") with a single, modern, animated
  QA Agility / HRSD Solution landing page that links to the login screen.
* Reskins the existing Odoo login page (background, logo, colours only)
  without touching any of its authentication functionality.
""",
    'author': 'QA Agility Technologies',
    'website': 'https://qaagility.com',
    'depends': ['web', 'website'],
    'data': [
        'views/homepage_templates.xml',
        'views/login_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'hrsd_landing/static/src/scss/variables.scss',
            'hrsd_landing/static/src/scss/landing.scss',
            'hrsd_landing/static/src/scss/login.scss',
            'hrsd_landing/static/src/js/landing.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
