{
    'name': 'Flutter Attendance',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'GPS + photo attendance check-in/check-out API for the Flutter mobile app',
    'description': """
Flutter Attendance
===================
Attendance backend for the Flutter mobile app: GPS + photo check-in/check-out,
offline sync, dashboard and settings APIs. Builds on Flutter Login for JWT
authentication.

* POST /api/check-in, /api/check-out
* GET  /api/today, /api/history, /api/history/<id>
* PUT/DELETE /api/history/<id>  (HR only, beyond own remarks)
* GET/PUT /api/profile, POST /api/profile/photo
* GET  /api/dashboard, GET /api/settings
* POST /api/sync
* GET  /api/notifications, POST /api/notifications/<id>/read
""",
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'hr', 'flutterlogin'],
    'external_dependencies': {
        'python': ['geopy'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/shift_data.xml',
        'data/cron.xml',
        'views/attendance_views.xml',
        'views/device_views.xml',
        'views/shift_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
