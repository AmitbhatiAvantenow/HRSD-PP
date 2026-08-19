from odoo import http
from odoo.http import request

from odoo.addons.flutterattendance.controllers.attendance_api import _register_device
from odoo.addons.flutterlogin.controllers.auth_controller import _error, _json_body, _json_response, token_required


class FlutterNotificationPushController(http.Controller):

    @http.route('/api/push/register-token', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def register_token(self, employee=None, **kwargs):
        data = _json_body()
        platform = (data.get('platform') or '').strip().lower()
        if platform not in ('android', 'ios'):
            return _error("platform must be 'android' or 'ios'", 400)

        # Rides the same device-identity upsert check-in/check-out already
        # use, so a push token always lands on the same row as the device's
        # one-device-per-employee binding (flutterattendance.device.state) —
        # a revoked device can never keep receiving pushes.
        device = _register_device(request.env, employee, data, touch_field='last_sync')
        if not device:
            return _error('device_id is required', 400)

        vals = {'push_platform': platform}
        if platform == 'android':
            vals['fcm_token'] = data.get('fcm_token') or data.get('push_token')
        else:
            vals['apns_token'] = data.get('apns_token') or data.get('push_token')
        device.write(vals)
        return _json_response({'success': True})

    @http.route('/api/push/test', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def test_push(self, employee=None, **kwargs):
        request.env['flutternotification.push.service'].sudo().send_to_employee(
            employee,
            title='Test notification',
            body='Push notifications are configured correctly.',
            kind='test',
        )
        return _json_response({'success': True})
