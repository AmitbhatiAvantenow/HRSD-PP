from odoo import fields, http
from odoo.http import request

from odoo.addons.flutterlogin.controllers.auth_controller import token_required, _json_response, _error


def _notification_data(notif):
    return {
        'id': notif.id,
        'type': notif.notif_type,
        'title': notif.title,
        'body': notif.body or False,
        'for_date': notif.for_date.isoformat() if notif.for_date else False,
        'is_read': notif.is_read,
        'created_at': notif.create_date.isoformat() if notif.create_date else False,
    }


class FlutterAttendanceNotificationController(http.Controller):

    @http.route('/api/notifications', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def list_notifications(self, employee=None, unread_only=None, **kwargs):
        Notification = request.env['flutterattendance.notification'].sudo()
        domain = [('employee_id', '=', employee.id)]
        if (unread_only or '').lower() in ('1', 'true'):
            domain.append(('is_read', '=', False))
        notifications = Notification.search(domain, limit=50)
        return _json_response({
            'success': True,
            'unread_count': Notification.search_count([('employee_id', '=', employee.id), ('is_read', '=', False)]),
            'notifications': [_notification_data(n) for n in notifications],
        })

    @http.route('/api/notifications/<int:notif_id>/read', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    @token_required
    def mark_read(self, notif_id, employee=None, **kwargs):
        notification = request.env['flutterattendance.notification'].sudo().browse(notif_id).exists()
        if not notification or notification.employee_id.id != employee.id:
            return _error('Notification not found', 404)
        notification.write({'is_read': True, 'read_at': fields.Datetime.now()})
        return _json_response({'success': True})
