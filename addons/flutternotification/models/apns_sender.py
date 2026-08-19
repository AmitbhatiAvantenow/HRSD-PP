import logging
import time

import httpx
import jwt

_logger = logging.getLogger(__name__)

APNS_PROD_HOST = 'https://api.push.apple.com'
APNS_SANDBOX_HOST = 'https://api.sandbox.push.apple.com'
CHECKOUT_CATEGORY = 'CHECKOUT_ACTION'

# APNs allows (and expects) a provider JWT to be reused for repeated calls
# and rate-limits how often a fresh one may be issued for the same key —
# minting one per send would eventually get throttled.
_TOKEN_REUSE_SECONDS = 1800


class ApnsSender:
    """Sends iOS push notifications via Apple's direct HTTP/2 provider API.

    Deliberately not routed through Firebase — the app registers for raw
    APNs device tokens itself (see ios/Runner/AppDelegate.swift), so iOS
    push needs no Firebase project at all.
    """

    def __init__(self, env):
        icp = env['ir.config_parameter'].sudo()
        self._key_id = icp.get_param('flutternotification.apns_key_id')
        self._team_id = icp.get_param('flutternotification.apns_team_id')
        self._bundle_id = icp.get_param('flutternotification.apns_bundle_id')
        self._p8_key = icp.get_param('flutternotification.apns_p8_key')
        self._sandbox = icp.get_param('flutternotification.apns_use_sandbox') == 'True'
        self._cached_token = None
        self._cached_token_at = 0

    @property
    def is_configured(self):
        return bool(self._key_id and self._team_id and self._bundle_id and self._p8_key)

    def _provider_token(self):
        now = time.time()
        if self._cached_token and now - self._cached_token_at < _TOKEN_REUSE_SECONDS:
            return self._cached_token
        token = jwt.encode(
            {'iss': self._team_id, 'iat': int(now)},
            self._p8_key,
            algorithm='ES256',
            headers={'kid': self._key_id},
        )
        self._cached_token = token
        self._cached_token_at = now
        return token

    def send(self, device_token, title, body, data=None):
        """Returns (success, status_code_or_None, response_text)."""
        if not self.is_configured:
            return False, None, 'APNs is not configured (Settings > Mobile Attendance).'

        host = APNS_SANDBOX_HOST if self._sandbox else APNS_PROD_HOST
        url = f'{host}/3/device/{device_token}'
        payload = {
            'aps': {
                'alert': {'title': title, 'body': body},
                'category': CHECKOUT_CATEGORY,
                'sound': 'default',
            },
            **(data or {}),
        }
        headers = {
            'authorization': f'bearer {self._provider_token()}',
            'apns-topic': self._bundle_id,
            'apns-push-type': 'alert',
            'apns-priority': '10',
        }
        try:
            with httpx.Client(http2=True, timeout=10) as client:
                resp = client.post(url, json=payload, headers=headers)
        except Exception as exc:
            _logger.warning('flutternotification: APNs send failed: %s', exc, exc_info=True)
            return False, None, f'APNs send failed: {exc}'
        return resp.status_code == 200, resp.status_code, resp.text
