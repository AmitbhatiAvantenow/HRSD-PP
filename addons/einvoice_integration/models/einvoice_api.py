# -*- coding: utf-8 -*-
import json
import logging
import re
from datetime import timedelta

import requests

from odoo import _, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 30
# WhiteBooks doesn't document the auth-token TTL on the endpoints shown to us;
# NIC-backed e-Invoice GSPs commonly issue tokens valid ~6 hours, so we cache
# on that assumption and simply re-authenticate on any auth-looking failure.
TOKEN_LIFETIME_MINUTES = 6 * 60


def _find_key(data, *candidates):
    """Case/underscore-insensitive recursive search for the first of
    `candidates` present anywhere in a (possibly nested) API response.
    WhiteBooks' exact response envelope isn't documented for us, so instead
    of hard-coding one exact key path, we search broadly and let the caller
    supply every reasonable spelling of the key it wants."""
    wanted = {c.lower().replace('_', '') for c in candidates}

    def _walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(key, str) and key.lower().replace('_', '') in wanted:
                    if value not in (None, ''):
                        return value
            for value in node.values():
                found = _walk(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = _walk(item)
                if found is not None:
                    return found
        return None

    return _walk(data)


def _friendly_error(data, raw_text=None):
    """Best-effort extraction of a short, plain-English message from a
    WhiteBooks error response. WhiteBooks doesn't document one fixed error
    shape for us, and in practice its error payloads aren't even always
    valid JSON (unquoted keys, e.g. "[{ErrorCode:2258, ErrorMessage:...}]")
    - so alongside walking any JSON that did parse, this also regex-matches
    ErrorMessage text directly out of the raw response body, and either way
    drops the ErrorCode/braces/JSON-syntax noise instead of showing the raw
    payload to the user."""
    messages = []

    def _collect(node):
        if isinstance(node, dict):
            for key, value in node.items():
                key_l = key.lower().replace('_', '') if isinstance(key, str) else ''
                if key_l == 'errormessage' and isinstance(value, str) and value.strip():
                    messages.append(value.strip())
                elif key_l in ('errordetails', 'errors') and isinstance(value, str):
                    messages.extend(
                        m.strip() for m in re.findall(r'ErrorMessage\s*:\s*([^,}]+)', value))
                elif isinstance(value, (dict, list)):
                    _collect(value)
        elif isinstance(node, list):
            for item in node:
                _collect(item)

    if data is not None:
        _collect(data)
    if not messages and raw_text:
        messages.extend(m.strip() for m in re.findall(r'ErrorMessage\s*:\s*([^,}]+)', raw_text))
    if messages:
        return '; '.join(dict.fromkeys(messages))
    return _find_key(data, 'message', 'statusdesc', 'error') if data is not None else None


# Odoo's web client picks the plain "Invalid Operation" popup instead of the
# full technical error dialog by matching the exception's fully-qualified
# class name against the literal string "odoo.exceptions.UserError" - a
# subclass in this module's own path wouldn't match, so alias rather than
# subclass, to keep every WhiteBooks error showing as a simple popup.
EInvoiceApiError = UserError


class WhitebooksEInvoiceClient:
    """Thin client for a GST e-Invoice GSP's REST API (WhiteBooks by default,
    but nothing here is tied to that one provider).

    One instance is scoped to a single `res.company` record, which holds the
    Client ID/Secret, API username/password, GSTIN, base URL, endpoint paths
    and header names - see `models/res_company.py`. The IRN JSON payload
    itself follows the government's standard NIC e-Invoice schema, which
    every GSP has to accept as-is; what genuinely differs GSP to GSP is the
    URL routing and header naming, and those are exactly what's configurable
    here (Settings > e-Invoice > Advanced), so switching providers is a
    Settings change, not a code change.
    """

    def __init__(self, company):
        self.company = company
        if not company.einvoice_base_url:
            raise EInvoiceApiError(_(
                "No e-Invoice API Base URL is configured. Set it under "
                "Invoicing > Configuration > Settings > e-Invoice (GST)."))
        for field, label in (
            ('einvoice_client_id', "Client ID"),
            ('einvoice_client_secret', "Client Secret"),
            ('einvoice_username', "API Username"),
            ('einvoice_password', "API Password"),
            ('einvoice_ip_address', "Client IP"),
        ):
            if not company[field]:
                raise EInvoiceApiError(_(
                    "e-Invoice %(label)s is not configured. Set it under "
                    "Invoicing > Configuration > Settings > e-Invoice (GST).",
                    label=label))
        for field, label in (
            ('einvoice_path_authenticate', "Authenticate path"),
            ('einvoice_path_generate_irn', "Generate IRN path"),
            ('einvoice_path_get_irn', "Get IRN Details path"),
            ('einvoice_path_cancel_irn', "Cancel IRN path"),
            ('einvoice_path_generate_ewaybill', "Generate E-Way Bill path"),
            ('einvoice_path_get_ewaybill', "Get E-Way Bill Details path"),
            ('einvoice_header_client_id', "Client ID header name"),
            ('einvoice_header_client_secret', "Client Secret header name"),
            ('einvoice_header_username', "Username header name"),
            ('einvoice_header_password', "Password header name"),
            ('einvoice_header_ip_address', "Client IP header name"),
            ('einvoice_header_gstin', "GSTIN header name"),
            ('einvoice_header_auth_token', "Auth Token header name"),
        ):
            if not company[field]:
                raise EInvoiceApiError(_(
                    "e-Invoice Advanced setting \"%(label)s\" is not configured. "
                    "Set it under Invoicing > Configuration > Settings > "
                    "e-Invoice (GST) > Advanced.", label=label))
        self.base_url = company.einvoice_base_url.rstrip('/')
        self.gstin = company.einvoice_gstin or company.vat or ''
        if not self.gstin:
            raise EInvoiceApiError(_(
                "No GSTIN is configured for e-Invoicing. Set the company's "
                "Tax ID (GSTIN) or the e-Invoice GSTIN override in Settings."))

    # ------------------------------------------------------------------
    # Low-level plumbing
    # ------------------------------------------------------------------
    def _base_headers(self):
        c = self.company
        return {
            c.einvoice_header_client_id: c.einvoice_client_id,
            c.einvoice_header_client_secret: c.einvoice_client_secret,
            c.einvoice_header_username: c.einvoice_username,
            c.einvoice_header_ip_address: c.einvoice_ip_address,
            c.einvoice_header_gstin: self.gstin,
        }

    def _request(self, method, path, *, headers=None, params=None, json_body=None):
        url = f'{self.base_url}{path}'
        all_headers = {**self._base_headers(), **(headers or {})}
        _logger.info("e-Invoice API call: %s %s", method, path)
        try:
            response = requests.request(
                method, url, headers=all_headers, params=params,
                json=json_body, timeout=TIMEOUT)
        except requests.exceptions.RequestException as exc:
            raise EInvoiceApiError(_(
                "Could not reach the e-Invoice API (%(url)s): %(error)s",
                url=url, error=str(exc))) from exc

        try:
            data = response.json()
        except ValueError:
            data = None

        if not response.ok:
            message = _friendly_error(data, response.text) or _(
                "The e-Invoice service returned an error (HTTP %(code)s) with no "
                "further details.", code=response.status_code)
            raise EInvoiceApiError(message)

        if data is None:
            data = {}

        error_list = _find_key(data, 'errordetails', 'errors')
        success = _find_key(data, 'success', 'statuscd', 'status')
        if error_list or success in (False, '0', 0):
            message = _friendly_error(data, response.text) or _(
                "The e-Invoice API rejected this request but did not say why.")
            raise EInvoiceApiError(message)

        return data

    def _authenticated_headers(self):
        return {self.company.einvoice_header_auth_token: self._get_auth_token()}

    def _get_auth_token(self):
        company = self.company.sudo()
        if (company.einvoice_auth_token and company.einvoice_auth_token_expiry
                and company.einvoice_auth_token_expiry > fields.Datetime.now()):
            return company.einvoice_auth_token
        return self.authenticate()

    # ------------------------------------------------------------------
    # Public API operations
    # ------------------------------------------------------------------
    def authenticate(self):
        data = self._request(
            'GET', self.company.einvoice_path_authenticate,
            headers={self.company.einvoice_header_password: self.company.einvoice_password},
            params={'email': self.company.env.user.email or self.company.email or ''})
        token = _find_key(data, 'authtoken', 'token', 'accesstoken')
        if not token:
            raise EInvoiceApiError(_(
                "e-Invoice authentication did not return a token. "
                "Raw response: %(body)s", body=json.dumps(data)[:1000]))
        self._store_token(token)
        return token

    def _store_token(self, token):
        self.company.sudo().write({
            'einvoice_auth_token': token,
            'einvoice_auth_token_expiry': fields.Datetime.now() + timedelta(
                minutes=TOKEN_LIFETIME_MINUTES),
        })

    def _call_authenticated(self, method, path, **kwargs):
        """Call an endpoint that needs `auth-token`, transparently
        re-authenticating once if the cached token turns out to be stale
        (WhiteBooks doesn't document a fixed TTL, so a live rejection is the
        only reliable signal)."""
        extra_headers = kwargs.pop('headers', {})
        try:
            return self._request(
                method, path, headers={**self._authenticated_headers(), **extra_headers},
                **kwargs)
        except EInvoiceApiError as exc:
            message = str(exc).lower()
            if 'token' in message or 'auth' in message or 'unauthor' in message:
                return self._request(
                    method, path,
                    headers={self.company.einvoice_header_auth_token: self.authenticate(),
                             **extra_headers},
                    **kwargs)
            raise

    def _email_param(self):
        return {'email': self.company.env.user.email or self.company.email or ''}

    def generate_irn(self, invoice_json):
        return self._call_authenticated(
            'POST', self.company.einvoice_path_generate_irn,
            params=self._email_param(), json_body=invoice_json)

    def get_irn_details(self, irn):
        return self._call_authenticated(
            'GET', self.company.einvoice_path_get_irn,
            params={**self._email_param(), 'param1': irn})

    def cancel_irn(self, irn, reason_code, remark):
        return self._call_authenticated(
            'POST', self.company.einvoice_path_cancel_irn,
            params=self._email_param(),
            json_body={'Irn': irn, 'CnlRsn': reason_code, 'CnlRem': remark})

    def generate_ewaybill(self, ewaybill_json):
        return self._call_authenticated(
            'POST', self.company.einvoice_path_generate_ewaybill,
            params=self._email_param(), json_body=ewaybill_json)

    def get_ewaybill_details(self, irn):
        return self._call_authenticated(
            'GET', self.company.einvoice_path_get_ewaybill,
            params={**self._email_param(), 'param1': irn})
