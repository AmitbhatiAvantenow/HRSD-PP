# -*- coding: utf-8 -*-
from odoo import fields, models


class MailTemplateLayout(models.AbstractModel):
    _name = 'mail.template.layout'
    _description = 'Modern Branded Email Layout Helper'

    def render_modern_email(self, title, body_content, preheader='', company=None):
        """Wrap ``body_content`` (Markup HTML) in the shared modern
        branded shell (mail_template.email_layout) and return the
        full HTML, ready to use as a mail.mail body_html."""
        company = company or self.env.company
        return self.env['ir.qweb']._render('mail_template.email_layout', {
            'company': company,
            'email_title': title,
            'preheader': preheader,
            'body_content': body_content,
            'current_year': fields.Date.context_today(self).year,
        })
