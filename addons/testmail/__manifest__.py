{
    'name': 'Test Mail',
    'version': '1.0',
    'category': 'Administration',
    'summary': 'Verify outgoing mail deliverability using testmail.app',
    'description': """
Sends a real email through Odoo's configured Outgoing Mail Server to a
disposable testmail.app inbox address, then queries testmail.app's JSON
API to confirm it actually arrived - a one-click end-to-end check that
outgoing mail is really working, not just that mail.mail queued it.
""",
    'author': 'My Company',
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/testmail_check_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
