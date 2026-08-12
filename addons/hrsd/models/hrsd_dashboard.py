# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import api, fields, models

STAT_CARD_DEFS = {
    'total_employees': {'icon': 'users', 'label': 'TOTAL EMPLOYEES', 'sub': 'Active staff members', 'color': 'blue'},
    'on_leave_today': {'icon': 'calendar-check', 'label': 'ON LEAVE TODAY', 'sub': 'Approved leaves', 'color': 'green'},
    'pending_requests': {'icon': 'clock', 'label': 'PENDING REQUESTS', 'sub': 'Leave & other requests', 'color': 'amber'},
    'payroll_this_month': {'icon': 'rupee', 'label': 'PAYROLL THIS MONTH', 'sub': 'Total payroll amount', 'color': 'purple'},
    'attendance_rate': {'icon': 'trending-up', 'label': 'ATTENDANCE RATE', 'sub': 'This month average', 'color': 'pink'},
}


def _time_ago(dt):
    if not dt:
        return ""
    now = datetime.now()
    delta = now - dt
    seconds = delta.total_seconds()
    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        m = int(seconds // 60)
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if seconds < 86400:
        h = int(seconds // 3600)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = int(seconds // 86400)
    if d < 30:
        return f"{d} day{'s' if d != 1 else ''} ago"
    mo = int(d // 30)
    return f"{mo} month{'s' if mo != 1 else ''} ago"


def _inr(amount):
    """Format an integer amount using Indian digit grouping, e.g. 1245000 -> 12,45,000."""
    amount = int(amount or 0)
    s = str(amount)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


def _next_birthday_delta(birthday, today):
    """Days until the next occurrence (this year or next) of a month/day."""
    try:
        this_year = birthday.replace(year=today.year)
    except ValueError:
        # 29 Feb on a non-leap year
        this_year = birthday.replace(year=today.year, day=28)
    if this_year < today:
        try:
            this_year = birthday.replace(year=today.year + 1)
        except ValueError:
            this_year = birthday.replace(year=today.year + 1, day=28)
    return (this_year - today).days, this_year


class HrEmployee(models.Model):
    _inherit = ['hr.employee']

    @api.model
    def get_hrsd_dashboard_data(self):
        env = self.env
        user = env.user

        # Group-based visibility, shared by stat cards, dashboard menus,
        # submenu items and top-nav links: no group set means visible to
        # everyone; administrators always see everything.
        is_admin = user._is_admin()
        user_group_ids = set(user.all_group_ids.ids)

        def _visible(rec):
            return is_admin or not rec.group_ids or bool(set(rec.group_ids.ids) & user_group_ids)

        today = fields.Date.context_today(env['hr.employee'])
        now_dt = datetime.now()
        day_start = datetime.combine(today, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        Employee = env['hr.employee'].sudo()
        total_employees = Employee.search_count([])

        # ---- On leave today / pending requests (hr_holidays) -------------
        on_leave_today = 0
        pending_requests = 0
        try:
            Leave = env['hr.leave'].sudo()
            on_leave_today = Leave.search_count([
                ('state', '=', 'validate'),
                ('date_from', '<=', day_end),
                ('date_to', '>=', day_start),
            ])
            pending_requests = Leave.search_count([('state', '=', 'confirm')])
        except Exception:
            pass

        # ---- Attendance rate (hr_attendance) ------------------------------
        attendance_rate = 0
        try:
            Attendance = env['hr.attendance'].sudo()
            present_today = Attendance.search_count([
                ('check_in', '>=', day_start),
                ('check_in', '<', day_end),
            ])
            if total_employees:
                attendance_rate = round(min(present_today, total_employees) / total_employees * 100)
        except Exception:
            pass

        # ---- Payroll this month (hr.payslip NET lines) -------------------
        payroll_amount = _inr(0)
        try:
            month_start = today.replace(day=1)
            if today.month == 12:
                month_end = today.replace(year=today.year + 1, month=1, day=1)
            else:
                month_end = today.replace(month=today.month + 1, day=1)
            PayslipLine = env['hr.payslip.line'].sudo()
            net_lines = PayslipLine.search([
                ('slip_id.state', 'in', ['done', 'verify']),
                ('slip_id.date_from', '>=', month_start),
                ('slip_id.date_from', '<', month_end),
                ('code', '=', 'NET'),
            ])
            payroll_amount = _inr(sum(line.total for line in net_lines))
        except Exception:
            pass

        # ---- Current user profile -----------------------------------------
        employee = Employee.search([('user_id', '=', user.id)], limit=1)
        if not employee:
            employee = Employee.search([], limit=1)

        display_name = employee.name or user.name or 'Guest'
        image_url = None
        if employee and employee.image_1920:
            image_url = f"/web/image/hr.employee/{employee.id}/image_1920"

        profile = {
            'name': display_name,
            'job_title': employee.job_title or employee.job_id.name or '—',
            'avatar_initials': ''.join([p[0] for p in display_name.split()[:2]]).upper(),
            'user_initial': display_name[:1].upper(),
            'employee_id': 'EMP%05d' % employee.id if employee else '—',
            'department': employee.department_id.name or '—',
            'email': employee.work_email or user.email or '—',
            'phone': employee.work_phone or employee.mobile_phone or '—',
            'joined': (employee.create_date or now_dt).strftime('%d %b %Y'),
            'image_url': image_url,
        }

        # ---- Hierarchy (manager chain + direct reports) -------------------
        ancestors = []
        node = employee.parent_id
        while node and len(ancestors) < 3:
            ancestors.insert(0, node)
            node = node.parent_id
        subordinates = Employee.search([('parent_id', '=', employee.id)], limit=5) if employee else Employee

        def _emp_card(emp, current=False):
            emp_image_url = None
            if emp and emp.image_1920:
                emp_image_url = f"/web/image/hr.employee/{emp.id}/image_1920"
            return {
                'name': emp.name,
                'role': emp.job_title or emp.job_id.name or '—',
                'initials': ''.join([p[0] for p in emp.name.split()[:2]]).upper(),
                'current': current,
                'image_url': emp_image_url,
            }

        hierarchy = [_emp_card(a) for a in ancestors]
        hierarchy.append(_emp_card(employee, current=True) if employee else
                          {'name': profile['name'], 'role': profile['job_title'], 'initials': profile['avatar_initials'], 'current': True})
        reports = [_emp_card(s) for s in subordinates]

        # ---- Recent activity feed -------------------------------------------
        activities = []
        try:
            recent_employees = Employee.search([], order='create_date desc', limit=3)
            for e in recent_employees:
                if e.create_date:
                    activities.append({
                        'icon': 'user', 'color': 'blue',
                        'title': f'New employee {e.name} joined',
                        'date': e.create_date,
                    })
        except Exception:
            pass
        try:
            Leave = env['hr.leave'].sudo()
            recent_leaves = Leave.search([('state', '=', 'validate')], order='write_date desc', limit=3)
            for lv in recent_leaves:
                activities.append({
                    'icon': 'calendar-check', 'color': 'green',
                    'title': f'Leave request approved for {lv.employee_id.name}',
                    'date': lv.write_date,
                })
        except Exception:
            pass
        activities.sort(key=lambda a: a['date'], reverse=True)
        activities = activities[:5]
        for a in activities:
            a['time_ago'] = _time_ago(a['date'])
            del a['date']

        # ---- Upcoming birthdays --------------------------------------------
        birthdays = []
        try:
            employees_with_bday = Employee.search([('birthday', '!=', False)])
            for e in employees_with_bday:
                delta_days, next_date = _next_birthday_delta(e.birthday, today)
                birthdays.append({
                    'name': e.name,
                    'role': e.job_title or e.job_id.name or '—',
                    'initials': ''.join([p[0] for p in e.name.split()[:2]]).upper(),
                    'date_str': next_date.strftime('%d %b'),
                    'delta_days': delta_days,
                    'in_str': 'Today' if delta_days == 0 else ('Tomorrow' if delta_days == 1 else f'In {delta_days} days'),
                })
            birthdays.sort(key=lambda b: b['delta_days'])
            birthdays = birthdays[:5]
        except Exception:
            birthdays = []

        # ---- Dashboard widget visibility (Recent Activities / Upcoming
        #      Birthdays panels — configurable from the backend at HR
        #      Portal > Dashboard Widgets). Unlike stat cards / dashboard
        #      menus / top-nav links, these default to Administrators-only:
        #      no group set means hidden from everyone but admins. ----------
        widgets_by_key = {w.key: w for w in env['hrsd.dashboard.widget'].sudo().search([])}

        def _widget_visible(key):
            widget = widgets_by_key.get(key)
            if widget is None or not widget.active:
                return False
            return is_admin or bool(set(widget.group_ids.ids) & user_group_ids)

        show_recent_activities = _widget_visible('recent_activities')
        show_upcoming_birthdays = _widget_visible('upcoming_birthdays')
        if not show_recent_activities:
            activities = []
        if not show_upcoming_birthdays:
            birthdays = []

        # ---- Stat cards (configurable from the backend at HR Portal >
        #      Stat Cards — controls which cards show for whom, and their
        #      order; the numbers themselves are always computed live). ----
        stat_values = {
            'total_employees': total_employees,
            'on_leave_today': on_leave_today,
            'pending_requests': pending_requests,
            'payroll_this_month': '₹%s' % payroll_amount,
            'attendance_rate': '%s%%' % attendance_rate,
        }
        stat_card_configs = env['hrsd.dashboard.stat.card'].sudo().search([]).filtered(_visible)
        stat_cards = [{
            'icon': STAT_CARD_DEFS[c.key]['icon'],
            'value': stat_values.get(c.key, ''),
            'label': STAT_CARD_DEFS[c.key]['label'],
            'sub': STAT_CARD_DEFS[c.key]['sub'],
            'color': STAT_CARD_DEFS[c.key]['color'],
        } for c in stat_card_configs if c.key in STAT_CARD_DEFS]

        # ---- Dashboard menus / submenu items (fully configurable from the
        #      backend at HR Portal > Dashboard Menus, no code changes) -----
        menus = env['hrsd.dashboard.menu'].sudo().search([]).filtered(_visible)
        ops_cards = [{
            'id': menu.id,
            'icon': menu.icon,
            'title': menu.name,
            'desc': menu.description or '',
            'color': menu.color,
            'url': menu.url or '',
        } for menu in menus]

        detail_data = {
            menu.id: {
                'title': menu.name,
                'desc': menu.description or '',
                'cards': [{
                    'icon': item.icon,
                    'color': item.color,
                    'title': item.name,
                    'desc': item.description or '',
                    'url': item.url,
                } for item in menu.submenu_ids if _visible(item)],
            } for menu in menus
        }

        # ---- Top navigation bar links (configurable from the backend at
        #      HR Portal > Top Navigation, no code changes) -----------------
        navbar_items = env['hrsd.dashboard.navbar.item'].sudo().search([]).filtered(_visible)
        nav_items = [{'name': item.name, 'url': item.url} for item in navbar_items]

        return {
            'profile': profile,
            'hierarchy': hierarchy,
            'reports': reports,
            'stat_cards': stat_cards,
            'ops_cards': ops_cards,
            'detail_data': detail_data,
            'nav_items': nav_items,
            'activities': activities,
            'birthdays': birthdays,
            'show_recent_activities': show_recent_activities,
            'show_upcoming_birthdays': show_upcoming_birthdays,
        }
