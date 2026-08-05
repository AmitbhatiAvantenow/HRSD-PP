# -*- coding: utf-8 -*-
import json

from markupsafe import Markup
from werkzeug.exceptions import Forbidden
from werkzeug.utils import redirect

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.utils import is_user_internal


def require_hrsd_confidential_access():
    """Gate the confidential HRSD features (E-Sign, Recruitment, Resume Screening,
    Interview Questions, Appraisal, Document OCR) to Administrators and HR Managers.
    Call at the top of every internal-facing route in those areas."""
    if not request.env.user.has_group('hrsd.group_hrsd_confidential'):
        raise Forbidden()


def get_hrsd_branding(env):
    """Portal name/logo, sourced from the current company so it stays in
    sync with Settings > General Settings > Companies (no hardcoded brand)."""
    company = env.company
    name = company.name or 'HR Portal'
    return {
        'name': name,
        'initial': name[:1].upper(),
        'logo_url': f'/web/image/res.company/{company.id}/logo' if company.logo else False,
    }


class HrsdRedirect(Home):

    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def index(self, s_action=None, db=None, **kw):
        if request.db and request.session.uid and is_user_internal(request.session.uid):
            return redirect('/hrsd/dashboard')
        return super().index(s_action=s_action, db=db, **kw)

    @http.route(['/web', '/odoo', '/odoo/<path:subpath>', '/scoped_app/<path:subpath>'],
                type='http', auth='none', readonly=Home._web_client_readonly)
    def web_client(self, s_action=None, **kw):
        # Only the bare /odoo entry point is redirected home — /odoo/<subpath> (settings,
        # specific actions, ...) and /web keep working normally for internal navigation.
        if (request.httprequest.path == '/odoo' and request.session.uid
                and is_user_internal(request.session.uid)):
            return redirect('/hrsd/dashboard')
        return super().web_client(s_action=s_action, **kw)


# ---- inline icon library used by the hrsd_dashboard_page template ----------
# Includes both the fixed portal-chrome icons (logout/grid/search/...) and the
# full configurable-dashboard icon set from dashboard.js's ICON_PATHS, so any
# icon chosen on an hrsd.dashboard.menu record renders correctly server-side.
_ICON_PATHS = {
    'logout': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    'grid': '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
    'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    'chevron-down': '<polyline points="6 9 12 15 18 9"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/>',
    'calendar-check': '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="m9 16 2 2 4-4"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    'rupee': '<path d="M6 3h12"/><path d="M6 8h12"/><path d="M6 13h5a4 4 0 0 0 0-8"/><path d="M6 13l8 8"/>',
    'trending-up': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    'briefcase': '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>',
    'badge': '<circle cx="12" cy="8" r="6"/><path d="M9 14.5 7 22l5-3 5 3-2-7.5"/>',
    'bot': '<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><path d="M8 16.5h.01" stroke-width="3" stroke-linecap="round"/><path d="M16 16.5h.01" stroke-width="3" stroke-linecap="round"/>',
    # configurable dashboard-menu icon set (mirrors dashboard.js ICON_PATHS)
    'userPlus': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M22 11h-6"/>',
    'shieldCheck': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    'shield': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>',
    'logOut': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    'target': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4"/>',
    'trendingUp': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    'award': '<circle cx="12" cy="8" r="6"/><path d="M9 14.5 7 22l5-3 5 3-2-7.5"/>',
    'calendarCheck': '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="m9 16 2 2 4-4"/>',
    'headset': '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3v5Z"/><path d="M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3v5Z"/>',
    'fileText': '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2Z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/>',
    'gift': '<rect x="3" y="8" width="18" height="13" rx="1"/><path d="M12 8v13"/><path d="M19 8a3 3 0 0 0 0-6 4 4 0 0 0-4 4 4 4 0 0 0-4-4 3 3 0 0 0 0 6Z"/>',
    'arrowRight': '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    'scan': '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="3" y1="12" x2="21" y2="12"/>',
    'messageCircle': '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    'chartBar': '<rect x="3" y="12" width="4" height="9" rx="1"/><rect x="10" y="7" width="4" height="14" rx="1"/><rect x="17" y="3" width="4" height="18" rx="1"/>',
}


def _icon(name):
    inner = _ICON_PATHS.get(name, '')
    return Markup(
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">' + inner + '</svg>'
    )


class HrsdDashboard(http.Controller):

    @http.route('/hrsd/dashboard', type='http', auth='user', website=False, sitemap=False)
    def dashboard(self, **kw):
        if not is_user_internal(request.session.uid):
            return redirect('/web/login')
        data = request.env['hr.employee'].get_hrsd_dashboard_data()
        data['detail_data_json'] = Markup(json.dumps(data.pop('detail_data')))
        data['icon'] = _icon
        data['brand'] = get_hrsd_branding(request.env)
        return request.render('hrsd.hrsd_dashboard_page', data)

    @http.route('/hrsign', type='http', auth='user', website=False, sitemap=False)
    def hr_sign(self, **kw):
        if not is_user_internal(request.session.uid):
            return redirect('/web/login')
        action = request.env.ref('hrsd.action_hr_esign_dashboard', raise_if_not_found=False)
        if action and getattr(action, 'id', False):
            return redirect(f'/odoo/action-{action.id}')
        return redirect('/hrsd/dashboard')
