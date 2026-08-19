from odoo import api, models

from .apns_sender import ApnsSender
from .fcm_sender import FcmSender


class FlutterNotificationPushService(models.AbstractModel):
    _name = 'flutternotification.push.service'
    _description = "Dispatches push notifications to an employee's active mobile device(s)"

    @api.model
    def send_to_employee(self, employee, title, body, data=None, kind='custom', attendance=None):
        """Sends `title`/`body` to every active device belonging to `employee`
        that has a registered push token, logging one flutternotification.push_log
        row per attempt — including the no-device/no-token/not-configured
        no-ops, so admins can see *why* nothing arrived instead of just
        silence (mirrors how flutterattendance.device.state already gates
        who's allowed to receive anything: a revoked/pending device is
        excluded by the 'active' filter below, same as it's excluded from
        check-in/out)."""
        Device = self.env['flutterattendance.device'].sudo()
        PushLog = self.env['flutternotification.push_log'].sudo()

        devices = Device.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'active'),
        ])
        if not devices:
            PushLog.create({
                'employee_id': employee.id,
                'kind': kind,
                'attendance_id': attendance.id if attendance else False,
                'state': 'skipped_no_token',
                'provider_response': 'No active device registered for this employee.',
            })
            return

        fcm = FcmSender(self.env)
        apns = ApnsSender(self.env)

        for device in devices:
            vals = {
                'employee_id': employee.id,
                'device_id': device.id,
                'kind': kind,
                'attendance_id': attendance.id if attendance else False,
                'platform': device.push_platform or False,
            }
            if device.push_platform == 'android' and device.fcm_token:
                ok, status, resp = fcm.send(device.fcm_token, title, body, data)
            elif device.push_platform == 'ios' and device.apns_token:
                ok, status, resp = apns.send(device.apns_token, title, body, data)
            else:
                PushLog.create({
                    **vals,
                    'state': 'skipped_no_token',
                    'provider_response': 'No push token registered for this device.',
                })
                continue

            PushLog.create({
                **vals,
                'state': 'sent' if ok else 'failed',
                'provider_status_code': status,
                'provider_response': (resp or '')[:2000],
            })
