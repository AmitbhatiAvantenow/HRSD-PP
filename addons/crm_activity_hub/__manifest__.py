# -*- coding: utf-8 -*-
{
    'name': 'CRM Activity Hub',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Modern tabbed activity panel for CRM opportunities',
    'description': """
Replaces the standard chatter on CRM opportunities with a tabbed panel:
Activity (merged feed of notes, calls, emails and documents), Conversation
(the standard messaging/composer experience), Documents (all attachments
with preview/download) and Timeline (stage-progression history).
""",
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['crm', 'mail'],
    'data': [
        'views/crm_lead_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_activity_hub/static/src/crm_activity_hub.scss',
            'crm_activity_hub/static/src/crm_activity_hub.js',
            'crm_activity_hub/static/src/crm_activity_hub.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
