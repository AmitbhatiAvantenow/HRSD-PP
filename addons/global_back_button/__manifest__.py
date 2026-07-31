# -*- coding: utf-8 -*-
{
    'name': 'Global Back Button',
    'version': '19.0.1.0.0',
    'summary': 'Quick Back Navigation in Backend Views',
    'description': """
Global Back Button
==================
Adds a universal Back button to all backend form views in Odoo 19,
allowing users to instantly return to the previous list/kanban/search view
with a single click — no breadcrumb hunting required.

Features:
- One-click navigation to previous view
- Works in all backend form views
- Minimal, non-intrusive UI integrated with Odoo's native control panel
- Saves navigation history per session
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Technical',
    'license': 'LGPL-3',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'global_back_button/static/src/css/global_back_button.css',
            'global_back_button/static/src/xml/global_back_button.xml',
            'global_back_button/static/src/js/global_back_button.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
