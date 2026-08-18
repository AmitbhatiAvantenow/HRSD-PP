import functools
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from odoo import fields, http
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)

JWT_ALGORITHM = 'HS256'
TOKEN_EXPIRY_SECONDS = 86400  # 24 hours


def _get_jwt_secret(env):
    """Return the signing secret for JWT tokens, generating and storing one on first use."""
    icp = env['ir.config_parameter'].sudo()
    secret = icp.get_param('flutterlogin.jwt_secret')
    if not secret:
        secret = secrets.token_hex(32)
        icp.set_param('flutterlogin.jwt_secret', secret)
    return secret


def _json_body():
    """Parse the raw JSON body of a type='http' request. Returns {} if empty/invalid."""
    try:
        raw = request.httprequest.get_data(as_text=True)
        return json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}


def _json_response(data, status=200):
    return request.make_json_response(data, status=status)


def _error(message, status=400):
    return _json_response({'success': False, 'error': message}, status=status)


def _employee_data(employee):
    return {
        'employee_id': employee.id,
        'employee_name': employee.name,
        'company': employee.company_id.name,
        'department': employee.department_id.name or False,
        'job_position': employee.job_id.name or False,
        'work_email': employee.work_email or False,
    }


def _enforce_device_binding(env, employee, data):
    """Registers/validates the logging-in device against the employee's
    one-device binding (flutterattendance.device.state).

    Returns (device_or_None, error_response_or_None). If the request
    doesn't include a device_id at all, binding is skipped rather than
    blocking the login — callers that don't send one (e.g. a future web
    login) aren't punished for it.
    """
    device_id_str = (data.get('device_id') or '').strip()
    if not device_id_str:
        return None, None

    Device = env['flutterattendance.device'].sudo()
    device = Device.search([('employee_id', '=', employee.id), ('device_id', '=', device_id_str)], limit=1)

    vals = {
        'employee_id': employee.id,
        'device_id': device_id_str,
        'device_name': data.get('device_name') or (device.device_name if device else False),
        'os_version': data.get('os_version') or (device.os_version if device else False),
        'app_version': data.get('app_version') or (device.app_version if device else False),
    }

    # "Multiple Device Login" security check (Mobile Attendance > Settings >
    # Security Checks). Enabled (default) -> the one-device binding below
    # is enforced, same as every other card on that screen where Enabled
    # means the named check is actively guarding check-in. Disabled ->
    # employees may be signed in on several devices at once, so skip the
    # binding entirely and just activate whichever device logs in.
    SecurityCheck = env['flutterattendance.security.check'].sudo()
    single_device_enforced = SecurityCheck.get_effective_settings(employee).get('multiple_device', True)
    if not single_device_enforced:
        if device:
            device.write({**vals, 'state': 'active'})
        else:
            device = Device.create({**vals, 'state': 'active'})
        return device, None

    active_elsewhere = Device.search([
        ('employee_id', '=', employee.id),
        ('state', '=', 'active'),
        ('device_id', '!=', device_id_str),
    ], limit=1)

    if device and device.state == 'active':
        device.write(vals)
        return device, None

    if active_elsewhere:
        if device:
            device.write({**vals, 'state': 'pending'})
        else:
            device = Device.create({**vals, 'state': 'pending'})
        other_name = active_elsewhere.device_name or 'another device'
        return None, _error(
            f"This account is already signed in on '{other_name}'. "
            "Ask your admin to approve this device before you can sign in here.",
            403,
        )

    # No other active device for this employee — first-ever login, or
    # their previously-active device was revoked/reset. Safe to activate
    # this one directly without needing admin approval.
    if device:
        device.write({**vals, 'state': 'active'})
    else:
        device = Device.create({**vals, 'state': 'active'})
    return device, None


def _generate_token(user, employee):
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user.id,
        'employee_id': employee.id,
        'company_id': employee.company_id.id,
        'jti': secrets.token_hex(16),
        'iat': now,
        'exp': now + timedelta(seconds=TOKEN_EXPIRY_SECONDS),
    }
    secret = _get_jwt_secret(request.env)
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM), payload


def _decode_token(token):
    """Decode and validate a Bearer token: signature, expiry, and revocation.

    Returns (payload, None) on success, or (None, error_response) on failure.
    """
    secret = _get_jwt_secret(request.env)
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None, _error('Token has expired', 401)
    except jwt.InvalidTokenError:
        return None, _error('Invalid token', 401)

    jti = payload.get('jti')
    if jti and request.env['flutterlogin.revoked.token'].sudo().search_count([('jti', '=', jti)]):
        return None, _error('Token has been revoked, please log in again', 401)
    return payload, None


def token_required(func):
    """Decorator for /api endpoints that must be called with a valid Bearer JWT.

    On success, switches request.env to the authenticated user and injects
    the resolved `employee` recordset and raw `token_payload` as keyword
    arguments to the endpoint.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        auth_header = request.httprequest.headers.get('Authorization', '')
        if not auth_header.lower().startswith('bearer '):
            return _error('Missing Authorization Bearer token', 401)
        token = auth_header[7:].strip()

        payload, error = _decode_token(token)
        if error:
            return error

        user = request.env['res.users'].sudo().browse(payload.get('user_id')).exists()
        if not user or not user.active:
            return _error('User not found or inactive', 401)

        employee = request.env['hr.employee'].sudo().browse(payload.get('employee_id')).exists()
        if not employee or not employee.active or not employee.mobile_app_access:
            return _error('Employee not allowed to use the mobile app', 403)

        request.update_env(user=user.id)
        kwargs['employee'] = employee
        kwargs['token_payload'] = payload
        return func(self, *args, **kwargs)
    return wrapper


class FlutterLoginController(http.Controller):

    @http.route('/api/login', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def login(self, **kwargs):
        data = _json_body()
        identifier = (data.get('email') or data.get('login') or '').strip()
        password = data.get('password') or ''

        if not identifier or not password:
            return _error('Email/Employee ID and password are required', 400)

        Employee = request.env['hr.employee'].sudo()
        login = identifier
        if not request.env['res.users'].sudo().search_count([('login', '=', identifier)]):
            domain = [('barcode', '=', identifier)]
            if identifier.isdigit():
                domain = ['|', ('id', '=', int(identifier))] + domain
            employee_by_id = Employee.search(domain, limit=1)
            if employee_by_id.user_id:
                login = employee_by_id.user_id.login

        credential = {'login': login, 'password': password, 'type': 'password'}
        try:
            auth_info = request.env['res.users']._login(credential, {'interactive': True})
        except AccessDenied:
            return _error('Invalid credentials', 401)

        uid = auth_info['uid']
        user = request.env['res.users'].sudo().browse(uid)
        employee = Employee.search([('user_id', '=', uid)], limit=1)

        if not employee:
            return _error('No employee record linked to this user', 403)
        if not employee.active:
            return _error('Employee account is inactive', 403)
        if not employee.mobile_app_access:
            return _error('This employee is not allowed to use the mobile app', 403)

        device, device_error = _enforce_device_binding(request.env, employee, data)
        if device_error:
            return device_error

        token, payload = _generate_token(user, employee)
        if device:
            device.write({'current_jti': payload['jti'], 'last_login': fields.Datetime.now()})

        response = {
            'success': True,
            'token': token,
            'expires_in': TOKEN_EXPIRY_SECONDS,
        }
        response.update(_employee_data(employee))
        return _json_response(response)

    @http.route('/api/profile', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def profile(self, employee=None, **kwargs):
        return _json_response({'success': True, **_employee_data(employee)})

    @http.route('/api/logout', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def logout(self, employee=None, token_payload=None, **kwargs):
        jti = token_payload.get('jti')
        if jti:
            request.env['flutterlogin.revoked.token'].sudo().create({
                'jti': jti,
                'user_id': token_payload.get('user_id'),
            })
        return _json_response({'success': True, 'message': 'Logged out'})

    @http.route('/api/refresh', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def refresh(self, employee=None, token_payload=None, **kwargs):
        # Rotate: issue a new token and revoke the one just used.
        old_jti = token_payload.get('jti')
        user = request.env['res.users'].sudo().browse(token_payload.get('user_id'))
        token, _payload = _generate_token(user, employee)
        if old_jti:
            request.env['flutterlogin.revoked.token'].sudo().create({
                'jti': old_jti,
                'user_id': user.id,
            })
        return _json_response({
            'success': True,
            'token': token,
            'expires_in': TOKEN_EXPIRY_SECONDS,
        })

    @http.route('/api/forgot-password', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def forgot_password(self, **kwargs):
        data = _json_body()
        identifier = (data.get('email') or data.get('login') or '').strip()
        if not identifier:
            return _error('Email is required', 400)

        try:
            request.env['res.users'].sudo().reset_password(identifier)
        except Exception:
            # Never reveal whether the account exists; log server-side for support.
            _logger.info("Password reset requested for unknown/failed login: %s", identifier)

        return _json_response({
            'success': True,
            'message': 'If an account exists for this email, a password reset link has been sent.',
        })
