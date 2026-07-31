# -*- coding: utf-8 -*-
{
    'name': 'Navbar Back Button',
    'version': '19.0.1.0.0',
    'summary': 'A Back button next to the Apps menu for one-click navigation',
    'description': """
Navbar Back Button
===================
Adds a "Back" button directly next to the Apps menu (the 9-dot grid icon)
in the top navigation bar, so you can return to whatever you were looking
at before without hunting through breadcrumbs.

Features:
- Always available, in the same spot, on every screen
- One click calls back to the previous view/state
- Matches Odoo's native navbar look, including dark mode
- Disabled (greyed out) when there is nothing to go back to
    """,
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Technical',
    'license': 'LGPL-3',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'navbar_back_button/static/src/scss/navbar_back_button.scss',
            'navbar_back_button/static/src/xml/navbar_back_button.xml',
            'navbar_back_button/static/src/js/navbar_back_button.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
