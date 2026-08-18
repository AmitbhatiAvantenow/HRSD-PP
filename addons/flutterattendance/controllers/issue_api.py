import base64

from odoo import http
from odoo.http import request

from odoo.addons.flutterlogin.controllers.auth_controller import token_required, _json_body, _json_response, _error
from odoo.addons.flutterattendance.controllers.attendance_api import _decode_photo, _register_device


def _issue_data(rec):
    return {
        'id': rec.id,
        'name': rec.name,
        'description': rec.description,
        'state': rec.state,
        'has_photo': bool(rec.photo),
        'has_video': bool(rec.video),
        'created_at': rec.create_date.isoformat() if rec.create_date else False,
    }


class FlutterAttendanceIssueController(http.Controller):

    @http.route('/api/issues', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def submit_issue(self, employee=None, **kwargs):
        """Files a "Report an Issue" complaint from the mobile app's Support
        Center screen. Photo/video are optional, base64-encoded (matching
        every other photo upload in this module)."""
        data = _json_body()
        description = (data.get('description') or '').strip()
        if not description:
            return _error('description is required', 400)

        device = _register_device(request.env, employee, data)
        photo_bytes = _decode_photo(data.get('photo'))
        video_bytes = _decode_photo(data.get('video'))

        Issue = request.env['flutterattendance.issue'].sudo()
        record = Issue.create({
            'employee_id': employee.id,
            'description': description,
            'photo': base64.b64encode(photo_bytes) if photo_bytes else False,
            'video': base64.b64encode(video_bytes) if video_bytes else False,
            'video_filename': data.get('video_filename') if video_bytes else False,
            'device_id': device.id if device else False,
        })
        return _json_response({'success': True, **_issue_data(record)})

    @http.route('/api/issues', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def list_issues(self, employee=None, **kwargs):
        """The employee's own past complaints, most recent first."""
        Issue = request.env['flutterattendance.issue'].sudo()
        issues = Issue.search([('employee_id', '=', employee.id)], limit=50)
        return _json_response({'success': True, 'issues': [_issue_data(i) for i in issues]})
