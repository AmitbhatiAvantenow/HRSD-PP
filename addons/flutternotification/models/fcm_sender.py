import json
import logging
import time

import jwt
import requests

_logger = logging.getLogger(__name__)

FCM_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
FCM_TOKEN_URL = 'https://oauth2.googleapis.com/token'  # noqa: S105 (not a secret, an endpoint)


class FcmSender:
    """Sends Android push notifications via FCM HTTP v1.

    Deliberately hand-rolls the OAuth2 JWT-bearer exchange with PyJWT +
    requests (both already installed as flutterlogin/Odoo-core deps) instead
    of adding the `google-auth` package for what is otherwise a ~15-line
    token exchange.
    """

    def __init__(self, env):
        icp = env['ir.config_parameter'].sudo()
        self._project_id = icp.get_param('flutternotification.firebase_project_id')
        raw_json = icp.get_param('flutternotification.firebase_service_account_json')
        try:
            self._service_account = json.loads(raw_json) if raw_json else None
        except ValueError:
            _logger.warning('flutternotification: firebase_service_account_json is not valid JSON')
            self._service_account = None

    @property
    def is_configured(self):
        return bool(self._project_id and self._service_account)

    def _access_token(self):
        now = int(time.time())
        assertion = jwt.encode({
            'iss': self._service_account['client_email'],
            'scope': FCM_SCOPE,
            'aud': FCM_TOKEN_URL,
            'iat': now,
            'exp': now + 3600,
        }, self._service_account['private_key'], algorithm='RS256')
        resp = requests.post(FCM_TOKEN_URL, data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion,
        }, timeout=10)
        resp.raise_for_status()
        return resp.json()['access_token']

    def send(self, token, title, body, data=None):
        """Returns (success, status_code_or_None, response_text)."""
        if not self.is_configured:
            return False, None, 'FCM is not configured (Settings > Mobile Attendance).'
        try:
            access_token = self._access_token()
        except Exception as exc:
            _logger.warning('flutternotification: FCM auth failed: %s', exc, exc_info=True)
            return False, None, f'FCM auth failed: {exc}'

        url = f'https://fcm.googleapis.com/v1/projects/{self._project_id}/messages:send'
        payload = {
            'message': {
                'token': token,
                'notification': {'title': title, 'body': body},
                'data': {k: str(v) for k, v in (data or {}).items()},
                'android': {
                    'priority': 'high',
                    'notification': {
                        'channel_id': 'checkout_reminders',
                        'click_action': 'CHECKOUT_ACTION',
                    },
                },
            },
        }
        try:
            resp = requests.post(
                url, json=payload,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
        except Exception as exc:
            _logger.warning('flutternotification: FCM send failed: %s', exc, exc_info=True)
            return False, None, f'FCM send failed: {exc}'
        return resp.ok, resp.status_code, resp.text
