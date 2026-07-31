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

        return _json_response({
            'success': True,
            'gps_radius_meters': int(icp.get_param('flutterattendance.gps_radius_meters', '200') or 200),
            'company_name': company.name,
            'attendance_rules': {
                'shift_name': shift.name if shift else False,
                'start_time': shift.start_time if shift else False,
                'end_time': shift.end_time if shift else False,
                'grace_minutes': shift.grace_minutes if shift else False,
                'half_day_hours': shift.half_day_hours if shift else False,
                'full_day_hours': shift.full_day_hours if shift else False,
            },
            'theme': icp.get_param('flutterattendance.theme', 'default'),
            'language': request.env.user.lang or company.partner_id.lang or 'en_US',
        })
