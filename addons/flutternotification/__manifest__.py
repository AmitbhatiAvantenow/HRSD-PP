{
    'name': 'Flutter Notification',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Push notifications (FCM + direct APNs) for the Flutter mobile attendance app',
    'description': """
Flutter Notification
=====================
Real push-notification delivery for the Flutter mobile attendance app, built
on top of Flutter Attendance's existing device registry
(flutterattendance.device).

* POST /api/push/register-token  -> register an FCM (Android) or APNs (iOS) token
* POST /api/push/test             -> send a test push to the calling employee
* Backup cron: pushes a "forgot to check out?" notification via FCM/APNs to
  anyone still checked in past the configured checkout-reminder time, as a
  safety net for when the app's on-device geofence-exit detection didn't
  fire (e.g. a force-stopped app).
* Settings > General Settings > Mobile Attendance: Firebase/APNs credentials.

Requires `pip install httpx[http2]` on the Odoo server for APNs delivery
(PyJWT/requests are already Flutter Login dependencies).
""",
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'hr', 'flutterlogin', 'flutterattendance'],
    'external_dependencies': {
        'python': ['PyJWT', 'requests', 'httpx'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/push_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
        'data/cron.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
