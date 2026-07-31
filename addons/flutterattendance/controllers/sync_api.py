import base64
import logging

from odoo import fields, http
from odoo.http import request

from odoo.addons.flutterlogin.controllers.auth_controller import token_required, _json_body, _json_response, _error
from .attendance_api import _decode_photo, _register_device

_logger = logging.getLogger(__name__)


class FlutterAttendanceSyncController(http.Controller):

    @http.route('/api/sync', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def sync(self, employee=None, **kwargs):
        """Batch-upload attendance actions the app queued while offline.

        Body: {"items": [{"client_uuid", "action": "check_in"|"check_out",
        "timestamp", "latitude", "longitude", "address", "accuracy", "photo",
        "device_id", "device_name", "os_version", "app_version", "battery",
        "network", "internet"}, ...]}
        Items are applied in the order received so check_in/check_out pairs
        resolve correctly.
        """
        data = _json_body()
        items = data.get('items') or []
        if not isinstance(items, list):
            return _error('items must be a list', 400)

        Attendance = request.env['flutterattendance.attendance'].sudo()
        SyncLog = request.env['flutterattendance.sync.log'].sudo()

        results = []
        for item in items:
            client_uuid = item.get('client_uuid')
            action = item.get('action')
            log = SyncLog.create({
                'employee_id': employee.id,
                'client_uuid': client_uuid,
                'action_type': action if action in ('check_in', 'check_out') else 'check_in',
                'status': 'uploading',
            })
            try:
                timestamp = fields.Datetime.to_datetime(item.get('timestamp')) or fields.Datetime.now()
                latitude = item.get('latitude')
                longitude = item.get('longitude')
                if latitude is None or longitude is None:
                    raise ValueError('latitude and longitude are required')

                photo_bytes = _decode_photo(item.get('photo'))

                if action == 'check_in':
                    if Attendance._find_open_session(employee):
                        raise ValueError('Already checked in for an open session')
                    device = _register_device(request.env, employee, item)
                    record = Attendance.create({
                        'employee_id': employee.id,
                        'attendance_date': timestamp.date(),
                        'check_in_time': timestamp,
                        'checkin_latitude': latitude,
                        'checkin_longitude': longitude,
                        'checkin_address': item.get('address'),
                        'checkin_accuracy': item.get('accuracy') or 0.0,
                        'checkin_photo': base64.b64encode(photo_bytes) if photo_bytes else False,
                        'device_id': device.id if device else False,
                        'checkin_battery': item.get('battery') or 0.0,
                        'checkin_network': item.get('network'),
                        'checkin_internet': item.get('internet', False),
                        'checkin_ip_address': request.httprequest.remote_addr,
                        'checkin_created_at': fields.Datetime.now(),
                    })
                elif action == 'check_out':
                    record = Attendance._find_open_session(employee)
                    if not record:
                        raise ValueError('No open check-in to close')
                    record.write({
                        'check_out_time': timestamp,
                        'checkout_latitude': latitude,
                        'checkout_longitude': longitude,
                        'checkout_address': item.get('address'),
                        'checkout_accuracy': item.get('accuracy') or 0.0,
                        'checkout_photo': base64.b64encode(photo_bytes) if photo_bytes else False,
                        'checkout_created_at': fields.Datetime.now(),
                    })
                else:
                    raise ValueError(f"Unknown action '{action}'")

                log.write({'status': 'completed', 'attendance_id': record.id, 'processed_at': fields.Datetime.now()})
                results.append({'client_uuid': client_uuid, 'success': True, 'attendance_id': record.id})
            except Exception as exc:
                log.write({'status': 'failed', 'error_message': str(exc), 'processed_at': fields.Datetime.now()})
                results.append({'client_uuid': client_uuid, 'success': False, 'error': str(exc)})

        return _json_response({'success': True, 'results': results})
