import logging
import re
import urllib.parse
from datetime import datetime

from markupsafe import Markup
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html_sanitize

_logger = logging.getLogger(__name__)

STATE_META = {
    'new':               {'label': 'New',               'badge': 'bg-primary text-white'},
    'in_progress':       {'label': 'Work in Progress',  'badge': 'bg-warning text-dark'},
    'pending':           {'label': 'Pending',            'badge': 'bg-secondary text-white'},
    'resolved':          {'label': 'Resolved',           'badge': 'bg-info text-dark'},
    'closed_complete':   {'label': 'Closed Complete',    'badge': 'bg-success text-white'},
    'closed_incomplete': {'label': 'Closed Incomplete',  'badge': 'bg-danger text-white'},
    'cancelled':         {'label': 'Cancelled',          'badge': 'bg-dark text-white'},
}


class HrServiceCatalogPortal(http.Controller):

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clean_html(self, html_value):
        """Return a safe Markup, stripping Odoo's data-oe-version wrapper div."""
        if not html_value:
            return Markup('')
        raw = str(html_value)
        # Remove the Odoo wrapper: <div data-oe-version="2.0">...</div>
        raw = re.sub(r'^\s*<div[^>]+data-oe-version[^>]*>\s*', '', raw)
        raw = re.sub(r'\s*</div>\s*$', '', raw)
        return Markup(html_sanitize(raw, strip_style=True, strip_classes=False))

    def _get_employee(self):
        return request.env['hr.employee'].search(
            [('user_id', '=', request.env.uid)], limit=1
        )

    def _time_left_str(self, escalate_dt):
        """Return human-readable time left until escalation, or '0 Seconds' if past."""
        if not escalate_dt:
            return '—'
        now = datetime.now()
        if hasattr(escalate_dt, 'replace'):
            delta = escalate_dt - now
        else:
            return '—'
        total = int(delta.total_seconds())
        if total <= 0:
            return '0 Seconds'
        if total < 60:
            return '%d Second%s' % (total, 's' if total != 1 else '')
        if total < 3600:
            m = total // 60
            return '%d Minute%s' % (m, 's' if m != 1 else '')
        if total < 86400:
            h = total // 3600
            return '%d Hour%s' % (h, 's' if h != 1 else '')
        d = total // 86400
        return '%d Day%s' % (d, 's' if d != 1 else '')

    # ── Catalog page ─────────────────────────────────────────────────────────

    @http.route('/hr/service-request', auth='user', type='http', methods=['GET'], website=True)
    def catalog(self, **kwargs):
        producers = request.env['hr.case.producer'].search([('active', '=', True)])
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        descriptions = {p.id: self._clean_html(p.description) for p in producers}
        return request.render('hr_case_management.portal_catalog', {
            'producers': producers,
            'base_url': base_url,
            'descriptions': descriptions,
        })

    # ── Individual form page ──────────────────────────────────────────────────

    @http.route('/hr/service-request/<int:producer_id>',
                auth='user', type='http', methods=['GET'], website=True)
    def form_view(self, producer_id, error=None, **kwargs):
        producer = request.env['hr.case.producer'].browse(producer_id)
        if not producer.exists() or not producer.active:
            return request.not_found()

        employee = self._get_employee()
        all_employees = request.env['hr.employee'].search(
            [('active', '=', True)], order='name'
        )
        return request.render('hr_case_management.portal_form', {
            'producer': producer,
            'producer_description': self._clean_html(producer.description),
            'employee': employee,
            'all_employees': all_employees,
            'error': error and urllib.parse.unquote_plus(error) or False,
        })

    # ── Form submit — POST handler ────────────────────────────────────────────

    @http.route('/hr/service-request/<int:producer_id>/submit',
                auth='user', type='http', methods=['POST'], website=True, csrf=True)
    def form_submit(self, producer_id, **post):
        producer = request.env['hr.case.producer'].browse(producer_id)
        if not producer.exists() or not producer.active:
            return request.not_found()

        def _redirect_error(msg):
            return request.redirect(
                '/hr/service-request/%d?error=%s' % (
                    producer_id, urllib.parse.quote_plus(msg)
                )
            )

        employee = self._get_employee()
        if not employee:
            return _redirect_error(
                "Your account is not linked to an employee profile. "
                "Please contact HR."
            )

        short_description = (post.get('short_description') or '').strip()
        if not short_description:
            return _redirect_error("Please enter a Subject / Summary before submitting.")

        try:
            submission = request.env['hr.case.submission'].create({
                'producer_id': producer.id,
                'employee_id': employee.id,
                'short_description': short_description,
            })

            for q in producer.question_ids.sorted('sequence'):
                field_key = 'q_%d' % q.id
                raw = post.get(field_key, '')
                vals = {
                    'submission_id': submission.id,
                    'question_id': q.id,
                }
                ft = q.field_type
                if ft == 'text':
                    vals['value_char'] = raw
                elif ft == 'textarea':
                    vals['value_text'] = raw
                elif ft == 'date':
                    vals['value_date'] = raw or False
                elif ft == 'boolean':
                    vals['value_boolean'] = raw == '1'
                elif ft == 'employee':
                    vals['value_employee_id'] = int(raw) if raw and raw.isdigit() else False
                elif ft == 'selection':
                    vals['value_selection'] = raw
                request.env['hr.case.submission.answer'].create(vals)

            submission.action_submit()

        except (UserError, ValidationError) as exc:
            return _redirect_error(str(exc))
        except Exception:
            _logger.exception("Unexpected error submitting HR service request")
            return _redirect_error("An unexpected error occurred. Please try again.")

        return request.redirect('/hr/service-request/done/%d' % submission.id)

    # ── Confirmation page ─────────────────────────────────────────────────────

    @http.route('/hr/service-request/done/<int:submission_id>',
                auth='user', type='http', methods=['GET'], website=True)
    def confirmation(self, submission_id, **kwargs):
        submission = request.env['hr.case.submission'].browse(submission_id)
        if not submission.exists():
            return request.redirect('/hr/service-request')
        case = submission.case_id.sudo()
        state_info = STATE_META.get(case.state, {'label': case.state, 'badge': 'bg-secondary'}) if case else {}
        return request.render('hr_case_management.portal_confirmation', {
            'submission': submission,
            'case': case,
            'state_info': state_info,
        })

    # ── My Requests list ──────────────────────────────────────────────────────

    @http.route('/hr/my-requests', auth='user', type='http', methods=['GET'], website=True)
    def my_requests(self, filter='all', search='', **kwargs):
        employee = self._get_employee()
        if not employee:
            return request.redirect('/hr/service-request')

        domain = [('employee_id', '=', employee.id)]
        if filter == 'open':
            domain += [('state', 'not in', ['closed_complete', 'closed_incomplete', 'cancelled'])]
        elif filter == 'closed':
            domain += [('state', 'in', ['closed_complete', 'closed_incomplete', 'cancelled'])]

        if search:
            domain += ['|', ('name', 'ilike', search), ('short_description', 'ilike', search)]

        cases = request.env['hr.case'].sudo().search(domain)
        return request.render('hr_case_management.portal_my_requests', {
            'cases': cases,
            'filter': filter,
            'search': search,
            'employee': employee,
            'state_meta': STATE_META,
        })

    # ── Request detail page ───────────────────────────────────────────────────

    @http.route('/hr/my-requests/<int:case_id>', auth='user', type='http', methods=['GET'], website=True)
    def case_detail(self, case_id, **kwargs):
        employee = self._get_employee()
        case = request.env['hr.case'].sudo().browse(case_id)
        if not case.exists():
            return request.redirect('/hr/my-requests')

        if employee and case.employee_id.id != employee.id:
            return request.not_found()

        submission = request.env['hr.case.submission'].sudo().search(
            [('case_id', '=', case.id)], limit=1
        )
        messages = case.sudo().message_ids.filtered(
            lambda m: m.message_type in ('comment', 'email')
        ).sorted('date', reverse=True)[:20]

        state_info = STATE_META.get(case.state, {'label': case.state, 'badge': 'bg-secondary'})
        time_left = self._time_left_str(case.will_escalate_on)

        PRIORITY_LABELS = dict(case._fields['priority'].selection)
        APPROVAL_LABELS = dict(case._fields['approval_state'].selection)

        return request.render('hr_case_management.portal_case_detail', {
            'case': case,
            'submission': submission,
            'messages': messages,
            'employee': employee,
            'state_meta': STATE_META,
            'state_info': state_info,
            'time_left': time_left,
            'priority_label': PRIORITY_LABELS.get(case.priority, '—'),
            'approval_label': APPROVAL_LABELS.get(case.approval_state, '—'),
        })
