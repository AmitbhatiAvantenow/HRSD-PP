import json
import logging

from markupsafe import Markup
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

STAGE_SELECTION = [
    ('to_do', 'To Do'),
    ('in_progress', 'In Progress'),
    ('in_review', 'In Review'),
    ('stuck', 'Stuck'),
    ('completed', 'Completed'),
]
PRIORITY_SELECTION = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]
PRIORITY_COLORS = {'low': 'gray', 'medium': 'blue', 'high': 'orange', 'critical': 'red'}
AVATAR_COLORS = ['purple', 'pink', 'blue', 'green', 'orange', 'indigo']


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------
def _json_body():
    try:
        data = request.httprequest.get_data(as_text=True)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return {}


def _ok(**kwargs):
    d = {'ok': True}
    d.update(kwargs)
    return request.make_response(json.dumps(d), headers=[('Content-Type', 'application/json')])


def _err(msg, status=400):
    return request.make_response(
        json.dumps({'ok': False, 'error': msg}),
        headers=[('Content-Type', 'application/json')],
        status=status,
    )


def _initials(name):
    words = [w for w in (name or '').split() if w]
    letters = ''.join(w[0] for w in words[:2]).upper()
    return letters or '?'


def _employee_brief(e):
    return {
        'id': e.id,
        'name': e.name,
        'initials': _initials(e.name),
        'color': AVATAR_COLORS[e.id % len(AVATAR_COLORS)],
    }


def _task_dict(t):
    return {
        'id': t.id,
        'name': t.name,
        'stage': t.stage,
        'priority': t.priority,
        'priority_label': dict(PRIORITY_SELECTION).get(t.priority, t.priority),
        'priority_color': PRIORITY_COLORS.get(t.priority, 'gray'),
        'tag': t.tag or '',
        'description': t.description or '',
        'date': t.date.strftime('%Y-%m-%d') if t.date else '',
        'hours': t.hours,
        'employee_id': t.employee_id.id,
        'employee_name': t.employee_id.name,
        'avatar_initials': _initials(t.employee_id.name),
        'avatar_color': AVATAR_COLORS[t.employee_id.id % len(AVATAR_COLORS)],
    }


def _all_subordinates(employee):
    """Employee plus every direct/indirect report, walked breadth-first."""
    result = employee
    frontier = employee
    while frontier:
        frontier = frontier.mapped('child_ids') - result
        result |= frontier
    return result


def _top_ancestor(employee):
    node = employee
    seen = employee.browse()
    while node.parent_id and node.parent_id not in seen:
        seen |= node
        node = node.parent_id
    return node


def _build_org_tree(employee, me_id, visible_ids):
    return {
        'id': employee.id,
        'name': employee.name,
        'initials': _initials(employee.name),
        'color': AVATAR_COLORS[employee.id % len(AVATAR_COLORS)],
        'is_me': employee.id == me_id,
        'is_visible': employee.id in visible_ids,
        'children': [_build_org_tree(c, me_id, visible_ids) for c in employee.child_ids],
    }


class TaskController(http.Controller):

    def _current_employee(self):
        return request.env['hr.employee'].sudo().search([('user_id', '=', request.env.uid)], limit=1)

    # -----------------------------------------------------------------------
    # Page
    # -----------------------------------------------------------------------
    @http.route('/hrsd/tasks', type='http', auth='user', website=False, sitemap=False)
    def tasks_page(self, **kw):
        employee = self._current_employee()
        if not employee:
            return request.render('hrsd.hrsd_tasks_page', {
                'page_data_json': Markup(json.dumps({'no_employee': True})),
            })

        visible = _all_subordinates(employee)
        visible_ids = set(visible.ids)
        root = _top_ancestor(employee)

        tasks = request.env['hr.task'].sudo().search([('employee_id', '=', employee.id)])

        timesheet_action = request.env.ref('hrsd.action_hr_timesheet_entry', raise_if_not_found=False)
        timesheet_url = f'/odoo/action-{timesheet_action.id}' if timesheet_action else False

        page_data = {
            'no_employee': False,
            'timesheet_url': timesheet_url,
            'me': _employee_brief(employee),
            'visible_employees': [_employee_brief(e) for e in visible.sorted('name')],
            'hierarchy': _build_org_tree(root, employee.id, visible_ids),
            'selected_employee_id': employee.id,
            'tasks': [_task_dict(t) for t in tasks],
            'priority_options': PRIORITY_SELECTION,
            'stage_options': STAGE_SELECTION,
        }
        return request.render('hrsd.hrsd_tasks_page', {
            'page_data_json': Markup(json.dumps(page_data)),
            'priority_options': PRIORITY_SELECTION,
            'stage_options': STAGE_SELECTION,
        })

    # -----------------------------------------------------------------------
    # List tasks for a chosen (visible) employee
    # -----------------------------------------------------------------------
    @http.route('/hrsd/tasks/list', type='http', auth='user', methods=['POST'], csrf=False)
    def tasks_list(self, **kw):
        employee = self._current_employee()
        if not employee:
            return _err('No employee profile linked to your user.', 403)

        body = _json_body()
        visible_ids = set(_all_subordinates(employee).ids)
        employee_id = int(body.get('employee_id') or employee.id)
        if employee_id not in visible_ids:
            return _err('Not authorized to view this employee.', 403)

        tasks = request.env['hr.task'].sudo().search([('employee_id', '=', employee_id)])
        return _ok(tasks=[_task_dict(t) for t in tasks])

    # -----------------------------------------------------------------------
    # Create / update task
    # -----------------------------------------------------------------------
    @http.route('/hrsd/tasks/save', type='http', auth='user', methods=['POST'], csrf=False)
    def task_save(self, **kw):
        employee = self._current_employee()
        if not employee:
            return _err('No employee profile linked to your user.', 403)

        body = _json_body()
        visible_ids = set(_all_subordinates(employee).ids)

        name = (body.get('name') or '').strip()
        if not name:
            return _err('Task title is required.')

        employee_id = int(body.get('employee_id') or employee.id)
        if employee_id not in visible_ids:
            return _err('Not authorized to assign tasks to this employee.', 403)

        def _float(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        vals = {
            'name': name,
            'employee_id': employee_id,
            'stage': body.get('stage') or 'to_do',
            'priority': body.get('priority') or 'medium',
            'tag': (body.get('tag') or '').strip(),
            'description': (body.get('description') or '').strip(),
            'date': body.get('date') or fields.Date.today().isoformat(),
            'hours': _float(body.get('hours')),
        }

        Task = request.env['hr.task'].sudo()
        try:
            task_id = body.get('id')
            if task_id:
                task = Task.browse(int(task_id))
                if not task.exists() or task.employee_id.id not in visible_ids:
                    return _err('Task not found.', 404)
                task.write(vals)
            else:
                task = Task.create(vals)
        except Exception as e:
            _logger.exception('task_save failed')
            return _err(str(e), 500)

        return _ok(task=_task_dict(task))

    # -----------------------------------------------------------------------
    # Drag-and-drop stage change
    # -----------------------------------------------------------------------
    @http.route('/hrsd/tasks/move', type='http', auth='user', methods=['POST'], csrf=False)
    def task_move(self, **kw):
        employee = self._current_employee()
        if not employee:
            return _err('No employee profile linked to your user.', 403)

        body = _json_body()
        visible_ids = set(_all_subordinates(employee).ids)

        task = request.env['hr.task'].sudo().browse(int(body.get('id') or 0))
        if not task.exists() or task.employee_id.id not in visible_ids:
            return _err('Task not found.', 404)

        stage = body.get('stage')
        if stage not in dict(STAGE_SELECTION):
            return _err('Invalid stage.')

        task.write({'stage': stage})
        return _ok(task=_task_dict(task))

    # -----------------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------------
    @http.route('/hrsd/tasks/delete', type='http', auth='user', methods=['POST'], csrf=False)
    def task_delete(self, **kw):
        employee = self._current_employee()
        if not employee:
            return _err('No employee profile linked to your user.', 403)

        body = _json_body()
        visible_ids = set(_all_subordinates(employee).ids)

        task = request.env['hr.task'].sudo().browse(int(body.get('id') or 0))
        if not task.exists() or task.employee_id.id not in visible_ids:
            return _err('Task not found.', 404)

        task.unlink()
        return _ok()
