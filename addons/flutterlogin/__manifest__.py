{
    'name': 'Flutter Login',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'JWT authentication API for the Flutter mobile attendance app',
    'description': """
Flutter Login
=============
Exposes a stateless JSON/JWT authentication API so a Flutter mobile app can
log employees in against this Odoo instance without using Odoo's web session
cookies.

* POST /api/login    -> authenticate with email/employee-id + password, get a JWT
* GET  /api/profile   -> sample protected endpoint, requires "Authorization: Bearer <token>"
""",
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'hr', 'auth_signup'],
    'external_dependencies': {
        'python': ['PyJWT'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
