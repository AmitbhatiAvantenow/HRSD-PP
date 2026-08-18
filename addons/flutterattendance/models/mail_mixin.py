import base64
import functools
import os
from email.message import EmailMessage as PyEmailMessage
from email.utils import make_msgid

from odoo import fields, models
from odoo.modules.module import get_module_path

BRAND_NAME = 'QA Agility'
BRAND_TAGLINE = 'Quant Analytics with Agility'
BRAND_WEBSITE = 'www.qaagility.com'
BRAND_SUPPORT_EMAIL = 'support@qaagility.com'
BRAND_BLUE = '#2451e0'

# Content-IDs for the two inline branding images. Referenced in the HTML as
# cid:<value> and matched against the Content-ID MIME header (which needs the
# angle brackets) when the message is assembled in _build_mime_message.
LOGO_CID = 'qaagility-logo@flutterattendance'
MARK_CID = 'qaagility-mark@flutterattendance'


@functools.lru_cache(maxsize=None)
def _brand_asset_bytes(filename):
    """Reads a module-bundled PNG once and caches the raw bytes.

    These are embedded as true inline (Content-ID) MIME attachments rather
    than data: URIs: Outlook's rendering engine either drops data: URI images
    outright or has them stripped by its content-safety scrubber, so the only
    reliably cross-client way to show a logo in an HTML email is as a real
    attachment referenced via cid:.
    """
    module_path = get_module_path('flutterattendance')
    if not module_path:
        return b''
    path = os.path.join(module_path, 'static', 'img', filename)
    if not os.path.isfile(path):
        return b''
    with open(path, 'rb') as f:
        return f.read()


class FlutterAttendanceMailMixin(models.AbstractModel):
    """Shared building blocks for every branded notification mail this addon
    sends (daily attendance summaries, issue-request notifications, ...):
    resolving employee/extra-email recipient lists, and hand-assembling the
    outgoing MIME message with true inline (cid:) logo images."""
    _name = 'flutterattendance.mail.mixin'
    _description = 'Flutter Attendance Mail Building Blocks'

    def _get_emails(self, employee_ids, extra):
        emails = [e for e in employee_ids.mapped('work_email') if e]
        if extra:
            emails += [e.strip() for e in extra.split(',') if e.strip()]
        seen = set()
        result = []
        for email in emails:
            key = email.lower()
            if key not in seen:
                seen.add(key)
                result.append(email)
        return result

    def _build_mime_message(self, *, subject, html_body, to_emails, cc_emails, attachments=None):
        """Builds the raw outgoing email by hand instead of going through
        mail.mail's normal send path. That path (ir.mail_server._build_email__)
        has no concept of inline Content-ID attachments -- every attachment it
        adds ends up as a regular (non-inline) one -- so a data: URI is the
        only way to embed an image through it, and Outlook's rendering engine
        either drops data: URIs or has them stripped by its content-safety
        scrubber. A true cid: image, sent as its own inline MIME part, is the
        one embedding method that actually survives across mail clients.

        :param attachments: optional list of {'filename', 'data' (bytes),
            'maintype', 'subtype'} dicts, added as regular (non-inline)
            attachments, e.g. an Excel export.
        """
        self.ensure_one()
        msg = PyEmailMessage()
        email_from = self.env.user.partner_id.email_formatted or self.env.company.email or 'noreply@localhost'
        msg['Subject'] = subject
        msg['From'] = email_from
        msg['Reply-To'] = email_from
        msg['To'] = ', '.join(to_emails)
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        msg['Date'] = fields.Datetime.now()
        msg['Message-Id'] = make_msgid()

        msg.set_content('This email requires an HTML-capable mail client to view.')
        msg.add_alternative(html_body, subtype='html')
        html_part = msg.get_payload()[-1]
        html_part.add_related(_brand_asset_bytes('qaagility_logo.png'), 'image', 'png', cid=f'<{LOGO_CID}>')
        html_part.add_related(_brand_asset_bytes('qaagility_mark.png'), 'image', 'png', cid=f'<{MARK_CID}>')

        for att in (attachments or []):
            msg.add_attachment(
                att['data'], maintype=att.get('maintype', 'application'),
                subtype=att.get('subtype', 'octet-stream'), filename=att['filename'],
            )
        return msg

    def _log_sent_mail(self, subject, body_html, to_emails, cc_emails, attachments=None):
        """Audit trail only: the actual delivery already happened via
        _build_mime_message + ir.mail_server, so this is created already
        'sent' rather than going through mail.mail's own send().

        :param attachments: optional list of {'filename', 'data' (bytes)}
            dicts, logged as regular ir.attachment records on the mail.mail.
        """
        attachment_vals = [(0, 0, {
            'name': att['filename'], 'datas': base64.b64encode(att['data']), 'type': 'binary',
        }) for att in (attachments or [])]
        self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_to': ','.join(to_emails),
            'email_cc': ','.join(cc_emails) if cc_emails else False,
            'auto_delete': False,
            'attachment_ids': attachment_vals,
            'state': 'sent',
        })
