# -*- coding: utf-8 -*-
from odoo import fields, models

# message_type values we don't want cluttering the Activity feed — these are
# system/tracking notifications, already covered by the Timeline tab.
_FEED_MESSAGE_TYPES = ('comment', 'email', 'email_outgoing')


def _iso(dt):
    return fields.Datetime.to_string(dt) if dt else False


def _attachment_payload(attachment):
    return {
        'id': attachment.id,
        'name': attachment.name,
        'mimetype': attachment.mimetype or '',
        'file_size': attachment.file_size,
    }


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def get_activity_hub_feed(self, offset=0, limit=15, search=''):
        """Merged, paginated feed for the Activity tab: notes, emails,
        pending scheduled activities and stand-alone document uploads.
        `search` filters across title/subtitle/author before pagination."""
        self.ensure_one()
        entries = []

        messages = self.env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('res_id', '=', self.id),
            ('message_type', 'in', _FEED_MESSAGE_TYPES),
        ])
        attached_ids = set()
        for msg in messages:
            attached_ids.update(msg.attachment_ids.ids)
            author = msg.author_id.name or msg.email_from or 'System'
            if msg.attachment_ids and not msg.preview:
                entries.append({
                    'id': 'message_%d' % msg.id,
                    'type': 'document_shared',
                    'icon': 'fa-file-text-o',
                    'color': 'indigo',
                    'title': 'Document shared',
                    'subtitle': ', '.join(msg.attachment_ids.mapped('name')),
                    'author': author,
                    'date': _iso(msg.date),
                    'attachments': [_attachment_payload(a) for a in msg.attachment_ids],
                })
            elif msg.message_type in ('email', 'email_outgoing'):
                entries.append({
                    'id': 'message_%d' % msg.id,
                    'type': 'email',
                    'icon': 'fa-envelope',
                    'color': 'orange',
                    'title': msg.subject or 'Email sent',
                    'subtitle': msg.preview or '',
                    'author': author,
                    'date': _iso(msg.date),
                })
            else:
                entries.append({
                    'id': 'message_%d' % msg.id,
                    'type': 'note',
                    'icon': 'fa-sticky-note-o',
                    'color': 'blue',
                    'title': 'Note added',
                    'subtitle': msg.preview or '',
                    'author': author,
                    'date': _iso(msg.date),
                })

        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.id),
        ])
        for act in activities:
            entries.append({
                'id': 'activity_%d' % act.id,
                'type': 'activity_scheduled',
                'icon': 'fa-calendar' if 'meeting' in (act.activity_type_id.name or '').lower() else 'fa-phone',
                'color': 'purple' if 'meeting' in (act.activity_type_id.name or '').lower() else 'green',
                'title': '%s scheduled' % (act.activity_type_id.name or 'Activity'),
                'subtitle': act.summary or '',
                'author': act.user_id.name or '',
                'date': _iso(act.date_deadline),
            })

        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.id),
            ('id', 'not in', list(attached_ids)),
        ])
        for att in attachments:
            entries.append({
                'id': 'attachment_%d' % att.id,
                'type': 'document_uploaded',
                'icon': 'fa-file-word-o' if 'word' in (att.mimetype or '') else 'fa-file-o',
                'color': 'indigo',
                'title': 'Document uploaded',
                'subtitle': att.name,
                'author': att.create_uid.name or '',
                'date': _iso(att.create_date),
                'attachments': [_attachment_payload(att)],
            })

        if search:
            needle = search.lower()
            entries = [
                e for e in entries
                if needle in ('%s %s %s' % (e['title'], e['subtitle'], e.get('author', ''))).lower()
            ]

        entries.sort(key=lambda e: e['date'] or '', reverse=True)
        total = len(entries)
        page = entries[offset:offset + limit]
        return {'items': page, 'has_more': offset + limit < total}

    def get_activity_hub_documents(self):
        """All attachments stored on this opportunity, for the Documents tab."""
        self.ensure_one()
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.id),
        ], order='create_date desc')
        return [{
            'id': att.id,
            'name': att.name,
            'mimetype': att.mimetype or '',
            'file_size': att.file_size,
            'create_date': _iso(att.create_date),
            'author': att.create_uid.name or '',
        } for att in attachments]

    def get_activity_hub_timeline(self):
        """Chronological stage-progression journey, for the Timeline tab."""
        self.ensure_one()
        entries = [{
            'id': 'created',
            'type': 'created',
            'icon': 'fa-flag-o',
            'color': 'blue',
            'title': 'Opportunity created',
            'subtitle': '',
            'date': _iso(self.create_date),
        }]

        tracking_values = self.env['mail.tracking.value'].search([
            ('mail_message_id.model', '=', 'crm.lead'),
            ('mail_message_id.res_id', '=', self.id),
            ('field_id.name', '=', 'stage_id'),
        ])
        for tv in tracking_values:
            entries.append({
                'id': 'stage_%d' % tv.id,
                'type': 'stage_change',
                'icon': 'fa-arrow-right',
                'color': 'purple',
                'title': 'Moved to %s' % (tv.new_value_char or '—'),
                'subtitle': 'from %s' % (tv.old_value_char or '—') if tv.old_value_char else '',
                'author': tv.mail_message_id.author_id.name or '',
                'date': _iso(tv.mail_message_id.date),
            })

        if self.won_status == 'won':
            entries.append({
                'id': 'won',
                'type': 'won',
                'icon': 'fa-trophy',
                'color': 'green',
                'title': 'Marked as Won',
                'subtitle': '',
                'date': _iso(self.date_closed) or _iso(self.write_date),
            })
        elif self.won_status == 'lost':
            entries.append({
                'id': 'lost',
                'type': 'lost',
                'icon': 'fa-times-circle-o',
                'color': 'red',
                'title': 'Marked as Lost',
                'subtitle': self.lost_reason_id.name or '',
                'date': _iso(self.date_closed) or _iso(self.write_date),
            })

        entries.sort(key=lambda e: e['date'] or '')
        return entries
