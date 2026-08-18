# -*- coding: utf-8 -*-
import base64

from odoo import fields, models
from odoo.tools.mimetypes import guess_mimetype

# Content-ID for the inline company-logo image (see build_mime_message).
LOGO_CID = 'company-logo@mail_template'


class MailTemplateLayout(models.AbstractModel):
    _name = 'mail.template.layout'
    _description = 'Modern Branded Email Layout Helper'

    def render_modern_email(self, title, body_content, preheader='', company=None, inline_logo=False):
        """Wrap ``body_content`` (Markup HTML) in the shared modern
        branded shell (mail_template.email_layout) and return the
        full HTML, ready to use as a mail.mail body_html.

        :param inline_logo: when True, the logo <img> references cid:LOGO_CID
            instead of the '/logo.png?company=..' relative URL. Pass True only
            when the caller will actually embed the logo as a true inline
            (Content-ID) attachment via build_mime_message below -- most mail
            clients (Outlook in particular) don't reliably fetch relative/
            data: URIs from an email at all, so the img would otherwise show
            as a broken image to the recipient.
        """
        company = company or self.env.company
        return self.env['ir.qweb']._render('mail_template.email_layout', {
            'company': company,
            'email_title': title,
            'preheader': preheader,
            'body_content': body_content,
            'current_year': fields.Date.context_today(self).year,
            'logo_cid': LOGO_CID if inline_logo else False,
        })

    def build_mime_message(self, *, subject, html_body, to_email, cc_emails=None, company=None, attachments=None):
        """Hand-builds the raw outgoing email instead of going through
        mail.mail's normal send path. That path (ir.mail_server._build_email__)
        has no concept of inline Content-ID attachments -- every attachment it
        adds ends up as a regular (non-inline) one -- so a data:/relative URI
        is the only way to embed an image through it, and that's exactly what
        renders as a broken image in Outlook and similar clients. A true cid:
        image, sent as its own inline MIME part, is the one embedding method
        that actually survives across mail clients.

        Use together with render_modern_email(..., inline_logo=True).

        :param attachments: optional list of {'filename', 'data' (bytes),
            'maintype', 'subtype'} dicts, added as regular (non-inline)
            attachments, e.g. a PDF.
        """
        from email.message import EmailMessage as PyEmailMessage
        from email.utils import make_msgid

        company = company or self.env.company
        msg = PyEmailMessage()
        email_from = self.env.user.partner_id.email_formatted or company.email or 'noreply@localhost'
        msg['Subject'] = subject
        msg['From'] = email_from
        msg['Reply-To'] = email_from
        msg['To'] = to_email
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        msg['Date'] = fields.Datetime.now()
        msg['Message-Id'] = make_msgid()

        msg.set_content('This email requires an HTML-capable mail client to view.')
        msg.add_alternative(html_body, subtype='html')

        if company.logo and not company.uses_default_logo:
            logo_bytes = base64.b64decode(company.logo)
            mimetype = guess_mimetype(logo_bytes, default='image/png')
            maintype, _slash, subtype = mimetype.partition('/')
            html_part = msg.get_payload()[-1]
            html_part.add_related(logo_bytes, maintype or 'image', subtype or 'png', cid=f'<{LOGO_CID}>')

        for att in (attachments or []):
            msg.add_attachment(
                att['data'], maintype=att.get('maintype', 'application'),
                subtype=att.get('subtype', 'octet-stream'), filename=att['filename'],
            )
        return msg
