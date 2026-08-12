import base64
import binascii
import json
import logging

from odoo import fields, http
from odoo.http import request

from odoo.addons.flutterlogin.controllers.auth_controller import token_required, _json_body, _json_response, _error
from odoo.addons.flutterattendance.models import face_engine

_logger = logging.getLogger(__name__)


def _decode_photo(b64_str):
    """Return raw bytes for a base64 (optionally data-URI prefixed) photo, or None."""
    if not b64_str:
        return None
    if b64_str.strip().startswith('data:') and ',' in b64_str:
        b64_str = b64_str.split(',', 1)[1]
    try:
        return base64.b64decode(b64_str)
    except (binascii.Error, ValueError):
        return None


def _attendance_data(rec):
    return {
        'id': rec.id,
        'attendance_date': rec.attendance_date.isoformat() if rec.attendance_date else False,
        'check_in_time': rec.check_in_time.isoformat() if rec.check_in_time else False,
        'check_out_time': rec.check_out_time.isoformat() if rec.check_out_time else False,
        'working_hours': rec.working_hours,
        'distance_km': rec.distance_km,
        'late_minutes': rec.late_minutes,
        'overtime_hours': rec.overtime_hours,
        'status': rec.status,
        'remarks': rec.remarks or False,
        'checkin': {
            'latitude': rec.checkin_latitude,
            'longitude': rec.checkin_longitude,
            'address': rec.checkin_address or False,
            'accuracy': rec.checkin_accuracy,
            'has_photo': bool(rec.checkin_photo),
            'photo_url': f'/api/attendance/{rec.id}/photo/checkin' if rec.checkin_photo else False,
            'battery': rec.checkin_battery,
            'network': rec.checkin_network or False,
            'internet': rec.checkin_internet,
            'ip_address': rec.checkin_ip_address or False,
            'created_at': rec.checkin_created_at.isoformat() if rec.checkin_created_at else False,
            'face_similarity': rec.checkin_face_similarity,
            'face_verified': rec.checkin_face_verified,
        },
        'checkout': {
            # Float fields default to 0.0 rather than False when unset, so
            # without this check a pending check-out looks like a real
            # (0, 0) coordinate to any client computing a distance from it.
            'latitude': rec.checkout_latitude if rec.check_out_time else False,
            'longitude': rec.checkout_longitude if rec.check_out_time else False,
            'address': rec.checkout_address or False,
            'accuracy': rec.checkout_accuracy if rec.check_out_time else False,
            'has_photo': bool(rec.checkout_photo),
            'photo_url': f'/api/attendance/{rec.id}/photo/checkout' if rec.checkout_photo else False,
            'created_at': rec.checkout_created_at.isoformat() if rec.checkout_created_at else False,
            'face_similarity': rec.checkout_face_similarity if rec.check_out_time else False,
            'face_verified': rec.checkout_face_verified if rec.check_out_time else False,
        },
        'device': rec.device_id.device_name if rec.device_id else False,
    }


def _register_device(env, employee, data, touch_field='last_sync'):
    """Upserts the flutterattendance.device row for whichever device sent
    this request (check-in or check-out both call this, each touching its
    own freshness field). No device_id in the payload -> no-op, same as
    the login-time registration this mirrors."""
    device_id_str = (data.get('device_id') or '').strip()
    if not device_id_str:
        return None
    Device = env['flutterattendance.device'].sudo()
    device = Device.search([('employee_id', '=', employee.id), ('device_id', '=', device_id_str)], limit=1)
    vals = {
        'employee_id': employee.id,
        'device_id': device_id_str,
        'device_name': data.get('device_name') or (device.device_name if device else False),
        'os_version': data.get('os_version') or (device.os_version if device else False),
        'app_version': data.get('app_version') or (device.app_version if device else False),
        touch_field: fields.Datetime.now(),
    }
    if device:
        device.write(vals)
        return device
    return Device.create(vals)


def _check_geofence(env, employee, latitude, longitude):
    """Reject check-in if this employee has a configured geofence location
    (specific or the primary fallback) and the point is outside its
    radius. Returns an error message, or None if no location is
    configured / the point is within range."""
    location = env['flutterattendance.location'].sudo().resolve_for_employee(employee)
    if not location:
        return None
    from geopy.distance import geodesic
    distance_m = geodesic((location.latitude, location.longitude), (float(latitude), float(longitude))).meters
    if distance_m > location.radius:
        return (f'You are {int(distance_m)}m from {location.name}; '
                f'check-in is only allowed within {location.radius}m.')
    return None


def _face_settings(env):
    ICP = env['ir.config_parameter'].sudo()
    threshold = float(ICP.get_param('flutterattendance.face_similarity_threshold', default='0.45'))
    max_attempts = int(ICP.get_param('flutterattendance.face_max_attempts', default='5'))
    return threshold, max_attempts


class FlutterAttendanceController(http.Controller):

    @http.route('/api/check-in', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def check_in(self, employee=None, **kwargs):
        data = _json_body()
        Attendance = request.env['flutterattendance.attendance'].sudo()

        if Attendance._find_open_session(employee):
            return _error('Already checked in. Please check out first.', 409)

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if latitude is None or longitude is None:
            return _error('latitude and longitude are required', 400)

        geofence_error = _check_geofence(request.env, employee, latitude, longitude)
        if geofence_error:
            return _error(geofence_error, 403)

        device = _register_device(request.env, employee, data)
        photo_bytes = _decode_photo(data.get('photo'))

        record = Attendance.create({
            'employee_id': employee.id,
            'attendance_date': fields.Date.context_today(employee),
            'check_in_time': fields.Datetime.now(),
            'checkin_latitude': latitude,
            'checkin_longitude': longitude,
            'checkin_address': data.get('address'),
            'checkin_accuracy': data.get('accuracy') or 0.0,
            'checkin_photo': base64.b64encode(photo_bytes) if photo_bytes else False,
            'device_id': device.id if device else False,
            'checkin_battery': data.get('battery') or 0.0,
            'checkin_network': data.get('network'),
            'checkin_internet': data.get('internet', True),
            'checkin_ip_address': request.httprequest.remote_addr,
            # Set by the app after a successful /api/face/verify call — absent
            # entirely when face_recognition is off, so this defaults safely.
            'checkin_face_similarity': data.get('face_similarity') or 0.0,
            'checkin_face_verified': bool(data.get('face_verified')),
        })
        return _json_response({'success': True, **_attendance_data(record)})

    @http.route('/api/check-out', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def check_out(self, employee=None, **kwargs):
        data = _json_body()
        Attendance = request.env['flutterattendance.attendance'].sudo()
        record = Attendance._find_open_session(employee)
        if not record:
            return _error('No open check-in found. Please check in first.', 409)

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if latitude is None or longitude is None:
            return _error('latitude and longitude are required', 400)

        _register_device(request.env, employee, data)
        photo_bytes = _decode_photo(data.get('photo'))
        vals = {
            'check_out_time': fields.Datetime.now(),
            'checkout_latitude': latitude,
            'checkout_longitude': longitude,
            'checkout_address': data.get('address'),
            'checkout_accuracy': data.get('accuracy') or 0.0,
            'checkout_photo': base64.b64encode(photo_bytes) if photo_bytes else False,
            'checkout_created_at': fields.Datetime.now(),
            'checkout_face_similarity': data.get('face_similarity') or 0.0,
            'checkout_face_verified': bool(data.get('face_verified')),
        }
        # Work comment collected from the app right after the check-out
        # selfie — optional so older app builds that don't send it yet
        # don't blank out anything.
        if data.get('remarks'):
            vals['remarks'] = data.get('remarks')
        record.write(vals)
        return _json_response({'success': True, **_attendance_data(record)})

    @http.route('/api/today', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def today(self, employee=None, **kwargs):
        Attendance = request.env['flutterattendance.attendance'].sudo()
        today = fields.Date.context_today(employee)
        records = Attendance.search([
            ('employee_id', '=', employee.id),
            ('attendance_date', '=', today),
        ], order='check_in_time asc')
        open_session = records.filtered(lambda r: not r.check_out_time)
        last_check_out = next((r.check_out_time for r in reversed(records) if r.check_out_time), False)
        return _json_response({
            'success': True,
            'records': [_attendance_data(r) for r in records],
            'is_checked_in': bool(open_session),
            'last_check_in': records[0].check_in_time.isoformat() if records else False,
            'last_check_out': last_check_out.isoformat() if last_check_out else False,
        })

    @http.route('/api/history', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def history(self, employee=None, date_from=None, date_to=None, limit=None, offset=None, **kwargs):
        Attendance = request.env['flutterattendance.attendance'].sudo()
        domain = [('employee_id', '=', employee.id)]
        if date_from:
            domain.append(('attendance_date', '>=', date_from))
        if date_to:
            domain.append(('attendance_date', '<=', date_to))
        try:
            limit = int(limit) if limit else 30
            offset = int(offset) if offset else 0
        except ValueError:
            limit, offset = 30, 0

        records = Attendance.search(domain, order='check_in_time desc', limit=limit, offset=offset)
        return _json_response({
            'success': True,
            'total': Attendance.search_count(domain),
            'records': [_attendance_data(r) for r in records],
        })

    @http.route('/api/history/<int:att_id>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def history_detail(self, att_id, employee=None, **kwargs):
        record = request.env['flutterattendance.attendance'].sudo().browse(att_id).exists()
        if not record or record.employee_id.id != employee.id:
            return _error('Attendance record not found', 404)
        return _json_response({'success': True, **_attendance_data(record)})

    @http.route('/api/history/<int:att_id>', type='http', auth='public', methods=['PUT'], csrf=False, cors='*')
    @token_required
    def history_update(self, att_id, employee=None, **kwargs):
        record = request.env['flutterattendance.attendance'].sudo().browse(att_id).exists()
        if not record:
            return _error('Attendance record not found', 404)

        is_owner = record.employee_id.id == employee.id
        is_hr = request.env.user.has_group('hr.group_hr_user')
        if not is_owner and not is_hr:
            return _error('Not authorized to edit this record', 403)

        data = _json_body()
        vals = {}
        if 'remarks' in data:
            # Any authenticated owner (or HR) may annotate their own record.
            vals['remarks'] = data.get('remarks')

        if is_hr:
            # Only HR may correct the underlying audit trail (times/status).
            for field_name in ('check_in_time', 'check_out_time'):
                if data.get(field_name):
                    parsed = fields.Datetime.to_datetime(data[field_name])
                    if not parsed:
                        return _error(f'Invalid datetime for {field_name}', 400)
                    vals[field_name] = parsed
            if data.get('status'):
                valid_codes = request.env['flutterattendance.status.rule'].sudo().with_context(
                    active_test=False).search([]).mapped('code')
                if data['status'] in valid_codes:
                    vals['status'] = data['status']

        if not vals:
            return _error('No editable fields provided', 400)

        record.write(vals)
        return _json_response({'success': True, **_attendance_data(record)})

    @http.route('/api/history/<int:att_id>', type='http', auth='public', methods=['DELETE'], csrf=False, cors='*')
    @token_required
    def history_delete(self, att_id, employee=None, **kwargs):
        if not request.env.user.has_group('hr.group_hr_user'):
            return _error('Only HR can delete attendance records', 403)
        record = request.env['flutterattendance.attendance'].sudo().browse(att_id).exists()
        if not record:
            return _error('Attendance record not found', 404)
        record.unlink()
        return _json_response({'success': True, 'message': 'Attendance record deleted'})

    @http.route('/api/attendance/<int:att_id>/photo/<string:which>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def attendance_photo(self, att_id, which, employee=None, **kwargs):
        record = request.env['flutterattendance.attendance'].sudo().browse(att_id).exists()
        is_hr = request.env.user.has_group('hr.group_hr_user')
        if not record or (record.employee_id.id != employee.id and not is_hr):
            return _error('Not found', 404)

        field_name = {'checkin': 'checkin_photo', 'checkout': 'checkout_photo'}.get(which)
        if not field_name:
            return _error('Invalid photo type, expected checkin or checkout', 400)

        photo_b64 = getattr(record, field_name)
        if not photo_b64:
            return request.not_found()
        return request.make_response(base64.b64decode(photo_b64), headers=[('Content-Type', 'image/jpeg')])

    @http.route('/api/face/verify', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def face_verify(self, employee=None, **kwargs):
        """Pre-flight face check, called before /api/check-in or
        /api/check-out. Never blocks by itself — the app decides what to do
        with match=false (retry, or escalate to /api/face/request-approval
        after enough attempts); this endpoint only ever reports a score."""
        data = _json_body()
        mode = data.get('mode')
        if mode not in ('check_in', 'check_out'):
            return _error("mode must be 'check_in' or 'check_out'", 400)

        threshold, max_attempts = _face_settings(request.env)
        settings = request.env['flutterattendance.security.check'].sudo().get_effective_settings(employee)
        if not settings.get('face_recognition'):
            return _json_response({
                'success': True, 'match': True, 'similarity': 1.0,
                'threshold': threshold, 'max_attempts': max_attempts, 'skipped': True,
            })

        photo_bytes = _decode_photo(data.get('photo'))
        if not photo_bytes:
            return _error('photo is required', 400)

        if not employee.face_embedding:
            return _json_response({
                'success': True, 'match': False, 'similarity': 0.0,
                'threshold': threshold, 'max_attempts': max_attempts, 'reason': 'no_reference_photo',
            })

        embedding = face_engine.embed_image_bytes(photo_bytes)
        if embedding is None:
            return _json_response({
                'success': True, 'match': False, 'similarity': 0.0,
                'threshold': threshold, 'max_attempts': max_attempts, 'reason': 'no_face_detected',
            })

        stored = json.loads(employee.face_embedding)
        similarity = face_engine.cosine_similarity(embedding, stored)
        return _json_response({
            'success': True,
            'match': similarity >= threshold,
            'similarity': round(similarity, 4),
            'threshold': threshold,
            'max_attempts': max_attempts,
        })

    @http.route('/api/face/request-approval', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def face_request_approval(self, employee=None, **kwargs):
        data = _json_body()
        mode = data.get('mode')
        if mode not in ('check_in', 'check_out'):
            return _error("mode must be 'check_in' or 'check_out'", 400)

        photo_bytes = _decode_photo(data.get('photo'))
        device = _register_device(request.env, employee, data)

        FaceApproval = request.env['flutterattendance.face.approval'].sudo()
        vals = {
            'employee_id': employee.id,
            'attendance_mode': mode,
            'photo': base64.b64encode(photo_bytes) if photo_bytes else False,
            'attempt_count': int(data.get('attempt_count') or 0),
            'similarity_score': float(data.get('similarity_score') or 0.0),
            'latitude': data.get('latitude') or 0.0,
            'longitude': data.get('longitude') or 0.0,
            'address': data.get('address'),
            'device_id': device.id if device else False,
        }
        # Reuse a still-pending request for this employee+mode instead of
        # piling up duplicates if the app retries the call.
        existing = FaceApproval.search([
            ('employee_id', '=', employee.id),
            ('attendance_mode', '=', mode),
            ('state', '=', 'pending'),
        ], limit=1)
        record = existing
        if existing:
            existing.write(vals)
        else:
            record = FaceApproval.create(vals)
        return _json_response({'success': True, 'request_id': record.id, 'status': record.state})

    @http.route('/api/face/request-approval/<int:request_id>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def face_request_approval_status(self, request_id, employee=None, **kwargs):
        record = request.env['flutterattendance.face.approval'].sudo().browse(request_id).exists()
        if not record or record.employee_id.id != employee.id:
            return _error('Request not found', 404)
        return _json_response({
            'success': True,
            'status': record.state,
            'attendance_id': record.attendance_id.id if record.attendance_id else False,
        })
