from odoo import fields, models


class FlutterAttendanceDevicePushExt(models.Model):
    _inherit = 'flutterattendance.device'

    apns_token = fields.Char(
        string='APNs Token',
        help="iOS device token for direct Apple Push Notification service delivery "
             "(flutternotification module). Android uses the existing fcm_token field.",
    )
    push_platform = fields.Selection(
        [('android', 'Android'), ('ios', 'iOS')],
        string='Push Platform',
        help="Which push service this device's token belongs to — set by "
             "POST /api/push/register-token, drives whether flutternotification "
             "sends via FCM or direct APNs.",
    )
