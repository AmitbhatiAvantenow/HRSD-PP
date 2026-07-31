import base64
import binascii
import io
import logging

from odoo import http
from odoo.http import request

from odoo.addons.flutterlogin.controllers.auth_controller import (
    token_required, _json_body, _json_response, _error, _employee_data,
)

_logger = logging.getLogger(__name__)

# Deliberately narrow: name/company/department/job are HR-managed, not self-service.
PROFILE_EDITABLE_FIELDS = ('mobile_phone', 'work_phone')


class FlutterAttendanceProfileController(http.Controller):

    @http.route('/api/profile', type='http', auth='public', methods=['PUT'], csrf=False, cors='*')
    @token_required
    def update_profile(self, employee=None, **kwargs):
        data = _json_body()
        vals = {k: v for k, v in data.items() if k in PROFILE_EDITABLE_FIELDS}
        if not vals:
            return _error(f"No editable fields provided. Editable: {', '.join(PROFILE_EDITABLE_FIELDS)}", 400)
        employee.sudo().write(vals)
        return _json_response({'success': True, **_employee_data(employee)})

    @http.route('/api/profile/photo', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def update_profile_photo(self, employee=None, **kwargs):
        data = _json_body()
        photo_b64 = data.get('photo')
        if not photo_b64:
            return _error('photo (base64) is required', 400)
        if photo_b64.strip().startswith('data:') and ',' in photo_b64:
            photo_b64 = photo_b64.split(',', 1)[1]

        try:
            raw = base64.b64decode(photo_b64)
        except (binascii.Error, ValueError):
            return _error('Invalid base64 photo data', 400)

        try:
            from PIL import Image
            Image.open(io.BytesIO(raw)).verify()
        except Exception:
            return _error('Uploaded file is not a valid image', 400)

        employee.sudo().write({'image_1920': base64.b64encode(raw)})
        return _json_response({'success': True, 'message': 'Profile photo updated'})
