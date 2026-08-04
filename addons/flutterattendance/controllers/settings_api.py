from odoo import http
from odoo.http import request

from odoo.addons.flutterlogin.controllers.auth_controller import token_required, _json_response


class FlutterAttendanceSettingsController(http.Controller):

    @http.route('/api/settings', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def settings(self, employee=None, **kwargs):
        icp = request.env['ir.config_parameter'].sudo()
        company = employee.company_id
        shift = employee.attendance_shift_id

        location = request.env['flutterattendance.location'].sudo().resolve_for_employee(employee)
        security_checks = request.env['flutterattendance.security.check'].sudo().get_effective_settings(employee)

        return _json_response({
            'success': True,
            'company_name': company.name,
            'attendance_rules': {
                'shift_name': shift.name if shift else False,
                'start_time': shift.start_time if shift else False,
                'end_time': shift.end_time if shift else False,
                'grace_minutes': shift.grace_minutes if shift else False,
                'half_day_hours': shift.half_day_hours if shift else False,
                'full_day_hours': shift.full_day_hours if shift else False,
            },
            'security_checks': security_checks,
            'face_recognition': {
                'similarity_threshold': float(icp.get_param('flutterattendance.face_similarity_threshold', '0.45')),
                'max_attempts': int(icp.get_param('flutterattendance.face_max_attempts', '5')),
            },
            'geofence': {
                'enabled': bool(location),
                'name': location.name if location else False,
                'latitude': location.latitude if location else False,
                'longitude': location.longitude if location else False,
                'radius_meters': location.radius if location else False,
            },
            'theme': icp.get_param('flutterattendance.theme', 'default'),
            'language': request.env.user.lang or company.partner_id.lang or 'en_US',
        })
