import base64
import binascii
import logging

from odoo import fields, http
from odoo.http import request

from odoo.addons.flutterlogin.controllers.auth_controller import token_required, _json_body, _json_response, _error

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
        },
        'checkout': {
            'latitude': rec.checkout_latitude,
            'longitude': rec.checkout_longitude,
            'address': rec.checkout_address or False,
            'accuracy': rec.checkout_accuracy,
            'has_photo': bool(rec.checkout_photo),
            'photo_url': f'/api/attendance/{rec.id}/photo/checkout' if rec.checkout_photo else False,
            'created_at': rec.checkout_created_at.isoformat() if rec.checkout_created_at else False,
        },
        'device': rec.device_id.device_name if rec.device_id else False,
    }


def _register_device(env, employee, data):
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
        'last_login': fields.Datetime.now(),
    }
    if device:
        device.write(vals)
        return device
    return Device.create(vals)


def _check_geofence(env, latitude, longitude):
    """Reject check-in if office coordinates + radius are configured and the
    point is outside the allowed radius. Returns an error message, or None."""
    icp = env['ir.config_parameter'].sudo()
    office_lat = icp.get_param('flutterattendance.office_latitude')
    office_lng = icp.get_param('flutterattendance.office_longitude')
    if not office_lat or not office_lng:
        return None
    from geopy.distance import geodesic
    radius_m = float(icp.get_param('flutterattendance.gps_radius_meters', '200') or 200)
    distance_m = geodesic((float(office_lat), float(office_lng)), (float(latitude), float(longitude))).meters
    if distance_m > radius_m:
        return f'You are {int(distance_m)}m from the office; check-in is only allowed within {int(radius_m)}m.'
    return None


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

        geofence_error = _check_geofence(request.env, latitude, longitude)
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

        photo_bytes = _decode_photo(data.get('photo'))
        record.write({
            'check_out_time': fields.Datetime.now(),
            'checkout_latitude': latitude,
            'checkout_longitude': longitude,
            'checkout_address': data.get('address'),
            'checkout_accuracy': data.get('accuracy') or 0.0,
            'checkout_photo': base64.b64encode(photo_bytes) if photo_bytes else False,
            'checkout_created_at': fields.Datetime.now(),
        })
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
            if data.get('status') in ('present', 'late', 'half_day'):
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
