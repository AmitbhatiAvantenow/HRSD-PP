# -*- coding: utf-8 -*-
import json
import secrets
from datetime import datetime

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

TESTMAIL_API_URL = 'https://api.testmail.app/api/json'


class TestmailCheck(models.Model):
    _name = 'testmail.check'
    _description = 'Outgoing Mail Deliverability Check (testmail.app)'
    _order = 'id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    tag = fields.Char(readonly=True, copy=False,
                       help='Unique per run, so each check queries testmail.app for '
                            'exactly the email this record sent - never a stale one.')
    namespace = fields.Char(
        default='ckb25', required=True,
        help='testmail.app namespace - the part before the dot in '
             '<namespace>.<tag>@inbox.testmail.app.')
    api_key = fields.Char(
        string='API Key', default='15f028de-ff02-4461-b654-0dbb257d07ae', required=True)
    to_email = fields.Char(compute='_compute_to_email', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent - Waiting for Delivery'),
        ('received', 'Received'),
        ('not_received', 'Not Received (timed out)'),
        ('error', 'Error'),
    ], default='draft', readonly=True, copy=False)
    sent_date = fields.Datetime(readonly=True, copy=False)
    received_date = fields.Datetime(readonly=True, copy=False)
    latency_seconds = fields.Float(readonly=True, copy=False)
    received_subject = fields.Char(readonly=True, copy=False)
    error_message = fields.Text(readonly=True, copy=False)
    raw_response = fields.Text(
        string='Raw API Response', readonly=True, copy=False,
        help='The last testmail.app JSON API response, kept for debugging.')

    @api.depends('namespace', 'tag')
    def _compute_to_email(self):
        for rec in self:
            rec.to_email = ('%s.%s@inbox.testmail.app' % (rec.namespace, rec.tag)
                             if rec.namespace and rec.tag else False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('tag'):
                vals['tag'] = 'odoo-%s-%s' % (
                    fields.Datetime.now().strftime('%Y%m%d%H%M%S'), secrets.token_hex(3))
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = vals['tag']
        return super().create(vals_list)

    def action_send_test_email(self):
        """Send a real email through Odoo's configured Outgoing Mail
        Server to this record's testmail.app tagged address. A
        successful "Check Inbox" afterwards is the only real proof
        outgoing mail works end-to-end - mail.mail reaching state
        'sent' only proves Odoo handed it to the SMTP server, not that
        it was actually delivered."""
        self.ensure_one()
        if not self.to_email:
            raise UserError(_('Set a namespace first.'))
        try:
            mail = self.env['mail.mail'].sudo().create({
                'subject': 'Odoo Test Mail - %s' % self.tag,
                'body_html': (
                    '<p>This is an automated deliverability test sent from Odoo.</p>'
                    '<p>Tag: %s<br/>Sent: %s</p>' % (self.tag, fields.Datetime.now())),
                'email_to': self.to_email,
                'auto_delete': False,
            })
            mail.send()
            if mail.state == 'exception':
                self.write({
                    'state': 'error',
                    'error_message': mail.failure_reason or _(
                        'mail.mail ended in "exception" state - check Settings > '
                        'Technical > Outgoing Mail Servers.'),
                })
                return
        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})
            return
        self.write({'state': 'sent', 'sent_date': fields.Datetime.now(), 'error_message': False})

    def action_check_inbox(self):
        """Query testmail.app's JSON API for this tag. Uses
        livequery=true so the call itself waits (up to ~60s) for the
        email to actually arrive instead of racing a fixed sleep -
        acceptable for a manual, one-off diagnostic button."""
        self.ensure_one()
        if self.state == 'draft':
            raise UserError(_('Send the test email first.'))
        try:
            resp = requests.get(TESTMAIL_API_URL, params={
                'apikey': self.api_key,
                'namespace': self.namespace,
                'tag': self.tag,
                'livequery': 'true',
                'limit': 1,
            }, timeout=70)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})
            return
        self.raw_response = json.dumps(data, indent=2)
        if data.get('result') != 'success':
            self.write({
                'state': 'error',
                'error_message': data.get('message') or _('testmail.app API call failed.'),
            })
            return
        emails = data.get('emails') or []
        if not emails:
            self.write({'state': 'not_received'})
            return
        email = emails[0]
        received_dt = datetime.utcfromtimestamp(email['timestamp'] / 1000.0)
        latency = (received_dt - self.sent_date).total_seconds() if self.sent_date else 0.0
        self.write({
            'state': 'received',
            'received_date': received_dt,
            'received_subject': email.get('subject'),
            'latency_seconds': latency,
            'error_message': False,
        })

    def action_send_and_verify(self):
        """One click: send, then immediately check - livequery makes
        the check wait for the email, so a single button press proves
        the whole outgoing-mail pipeline end-to-end."""
        self.ensure_one()
        self.action_send_test_email()
        if self.state == 'sent':
            self.action_check_inbox()
