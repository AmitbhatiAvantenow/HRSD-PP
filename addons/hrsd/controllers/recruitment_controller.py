import base64
import json
import logging
import os
import re

from markupsafe import Markup
from odoo import http, fields
from odoo.http import request

from .controllers import get_hrsd_branding
from .resume_controller import _extract_text, _extract_skills, _parse_resume

_logger = logging.getLogger(__name__)

PRIORITY_LABELS = {'1': '1 - Critical', '2': '2 - High', '3': '3 - Moderate', '4': '4 - Low'}
PRIORITY_COLORS = {'1': 'red', '2': 'green', '3': 'blue', '4': 'gray'}

STATUS_LABELS = {
    'not_started': 'Hiring Not Started',
    'in_progress': 'Hiring In Progress',
    'to_deploy': 'To be deployed',
    'deployed': 'Deployed',
    'completed': 'Assignment Completed',
    'cancelled': 'Close-Cancelled',
}
STATUS_TABS = [
    ('all', 'All'),
    ('not_started', 'Hiring Not Started'),
    ('in_progress', 'Hiring In Progress'),
    ('to_deploy', 'To be deployed'),
    ('deployed', 'Deployed'),
    ('completed', 'Assignment Completed'),
    ('cancelled', 'Close-Cancelled'),
]

INTERVIEW_STATUS_LABELS = {
    'to_interview': 'Candidate to be interviewed',
    'internal_screening': 'Internal Screening',
    'round_1': 'Interview Round 1',
    'round_2': 'Interview Round 2',
    'selected': 'Selected',
    'placed': 'Placed',
    'rejected': 'Rejected',
}

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


def _initials(text):
    words = [w for w in (text or '').split() if w]
    letters = ''.join(w[0] for w in words[:2]).upper()
    return letters or '?'


def _find_or_create_partner(name):
    name = (name or '').strip()
    if not name:
        return False
    Partner = request.env['res.partner'].sudo()
    partner = Partner.search([('name', '=ilike', name)], limit=1)
    if not partner:
        partner = Partner.create({'name': name, 'company_type': 'company'})
    return partner.id


def _find_or_create_employee(name):
    name = (name or '').strip()
    if not name:
        return False
    Employee = request.env['hr.employee'].sudo()
    employee = Employee.search([('name', '=ilike', name)], limit=1)
    if not employee:
        employee = Employee.create({'name': name})
    return employee.id


# ---------------------------------------------------------------------------
# Auto-fill a requirement from an uploaded job spec document
# ---------------------------------------------------------------------------
_LABEL_PATTERNS = {
    'job_title': r'(?:job\s*title|position|role)\s*[:\-]\s*(.+)',
    'client_name': r'(?:client|company|customer)(?:\s*name)?\s*[:\-]\s*(.+)',
    'client_contact_person': r'(?:contact\s*person|client\s*contact|point\s*of\s*contact)\s*[:\-]\s*(.+)',
    'skill': r'(?:required\s*skills?|skills?|key\s*skills?)\s*[:\-]\s*(.+)',
}


def _extract_labelled_field(text, pattern):
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return ''
    return m.group(1).strip().splitlines()[0].strip(' .')[:200]


def _extract_requirement_fields(text, filename):
    fields_out = {}
    for key, pattern in _LABEL_PATTERNS.items():
        fields_out[key] = _extract_labelled_field(text, pattern)

    if not fields_out['job_title']:
        first_line = next((l.strip() for l in text.splitlines() if l.strip()), '')
        fields_out['job_title'] = first_line[:120] or os.path.splitext(filename or 'New Requirement')[0]

    if not fields_out['skill']:
        detected = _extract_skills(text)
        fields_out['skill'] = ', '.join(detected[:8])

    fields_out['job_description'] = text.strip()[:8000] or fields_out['job_title']
    return fields_out


# ---------------------------------------------------------------------------
# Dict builders
# ---------------------------------------------------------------------------
def _requirement_to_dict(r, with_form=False):
    data = {
        'id': r.id,
        'code': r.code,
        'job_title': r.job_title,
        'client_name': r.client_name.name or '',
        'client_contact_person': r.client_contact_person or '',
        'coordinator': r.coordinator_id.name or '',
        'requestor': r.requestor_id.name or '',
        'assigned_to': r.assigned_to_id.name or '',
        'skill': r.skill or '',
        'priority': r.priority,
        'priority_label': PRIORITY_LABELS.get(r.priority, r.priority),
        'priority_color': PRIORITY_COLORS.get(r.priority, 'gray'),
        'status': r.status,
        'status_label': STATUS_LABELS.get(r.status, r.status),
        'job_description': r.job_description or '',
        'candidate_count': r.candidate_count,
        'note_count': r.note_count,
        'open_date': r.create_date.strftime('%Y-%m-%d %H:%M:%S') if r.create_date else '',
        'avatar_initials': _initials(r.job_title),
        'avatar_color': AVATAR_COLORS[r.id % len(AVATAR_COLORS)],
    }
    if with_form:
        data['form'] = {
            'id': r.id,
            'requirement_for': r.requirement_for or '',
            'client_name_id': r.client_name.id,
            'client_name': r.client_name.name or '',
            'client_contact_person': r.client_contact_person or '',
            'coordinator': r.coordinator_id.name or '',
            'requestor': r.requestor_id.name or '',
            'assigned_to': r.assigned_to_id.name or '',
            'skill': r.skill or '',
            'job_title': r.job_title,
            'priority': r.priority,
            'status': r.status,
            'job_description': r.job_description or '',
        }
    return data


def _candidate_to_dict(c):
    resume_url = None
    if c.resume_data:
        resume_url = f'/web/content/hr.recruitment.candidate/{c.id}/resume_data/{c.resume_filename or "resume"}'
    return {
        'id': c.id,
        'code': c.code,
        'name': c.name,
        'current_salary': c.current_salary,
        'expected_salary': c.expected_salary,
        'email': c.email or '',
        'mobile': c.mobile or '',
        'current_location': c.current_location or '',
        'experience_years': c.experience_years,
        'notice_period': c.notice_period.strftime('%Y-%m-%d') if c.notice_period else '',
        'interview_status': c.interview_status,
        'interview_status_label': INTERVIEW_STATUS_LABELS.get(c.interview_status, c.interview_status),
        'coordinator': c.coordinator_id.name or '',
        'closing_rate': c.closing_rate,
        'deployed': c.deployed,
        'resume_filename': c.resume_filename or '',
        'resume_url': resume_url,
        'avatar_initials': _initials(c.name),
        'avatar_color': AVATAR_COLORS[c.id % len(AVATAR_COLORS)],
    }


def _note_to_dict(n):
    return {
        'id': n.id,
        'author': n.author_id.name or '',
        'body': n.body or '',
        'create_date': n.create_date.strftime('%d %b %Y, %H:%M') if n.create_date else '',
    }


def _compute_stats(Requirement):
    total = Requirement.search_count([])
    Candidate = Requirement.env['hr.recruitment.candidate'].sudo()
    internal_screening = Candidate.search_count([('interview_status', '=', 'internal_screening')])
    interviews = Candidate.search_count([('interview_status', 'in', ('round_1', 'round_2'))])
    placed = Candidate.search_count([('interview_status', '=', 'placed')])
    return {
        'total': total,
        'internal_screening': internal_screening,
        'interviews': interviews,
        'placed': placed,
    }


PAGE_SIZE = 6


class RecruitmentController(http.Controller):

    # -----------------------------------------------------------------------
    # Careers-portal hub page
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment', type='http', auth='user', website=False, sitemap=False)
    def recruitment_page(self, **kw):
        return request.render('hrsd.hrsd_recruitment_page', {
            'user_name': request.env.user.name,
            'brand': get_hrsd_branding(request.env),
        })

    # -----------------------------------------------------------------------
    # Requirements dashboard page
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements', type='http', auth='user', website=False, sitemap=False)
    def requirements_page(self, **kw):
        Requirement = request.env['hr.recruitment'].sudo()
        domain = []
        total = Requirement.search_count(domain)
        requirements = Requirement.search(domain, limit=PAGE_SIZE, offset=0)

        Employee = request.env['hr.employee'].sudo()
        Partner = request.env['res.partner'].sudo()
        employees = [{'id': e.id, 'name': e.name} for e in Employee.search([], limit=500, order='name')]
        clients = [{'id': p.id, 'name': p.name} for p in Partner.search([('is_company', '=', True)], limit=500, order='name')]

        page_data = {
            'company_name': request.env.company.name,
            'stats': _compute_stats(Requirement),
            'requirements': [_requirement_to_dict(r) for r in requirements],
            'total': total,
            'page': 1,
            'page_size': PAGE_SIZE,
            'status': 'all',
            'search': '',
            'status_tabs': STATUS_TABS,
            'priority_options': list(PRIORITY_LABELS.items()),
            'status_options': list(STATUS_LABELS.items()),
            'interview_status_options': list(INTERVIEW_STATUS_LABELS.items()),
            'employees': employees,
            'clients': clients,
        }

        return request.render('hrsd.hrsd_recruitment_requirements_page', {
            'page_data_json': Markup(json.dumps(page_data)),
            'priority_options': page_data['priority_options'],
            'status_options': page_data['status_options'],
            'interview_status_options': page_data['interview_status_options'],
            'csrf_token': request.csrf_token(),
            'brand': get_hrsd_branding(request.env),
        })

    # -----------------------------------------------------------------------
    # List / filter / paginate
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements/list', type='http', auth='user', methods=['POST'], csrf=False)
    def requirements_list(self, **kw):
        body = _json_body()
        status = body.get('status') or 'all'
        search = (body.get('search') or '').strip()
        page = max(1, int(body.get('page') or 1))

        Requirement = request.env['hr.recruitment'].sudo()
        domain = [] if status == 'all' else [('status', '=', status)]
        if search:
            domain += ['|', '|', ('job_title', 'ilike', search), ('skill', 'ilike', search), ('client_name.name', 'ilike', search)]

        total = Requirement.search_count(domain)
        requirements = Requirement.search(domain, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)

        return _ok(
            requirements=[_requirement_to_dict(r) for r in requirements],
            total=total,
            page=page,
            page_size=PAGE_SIZE,
            stats=_compute_stats(Requirement),
        )

    # -----------------------------------------------------------------------
    # Create / update requirement
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements/save', type='http', auth='user', methods=['POST'], csrf=False)
    def requirement_save(self, **kw):
        body = _json_body()
        job_title = (body.get('job_title') or '').strip()
        skill = (body.get('skill') or '').strip()
        client_name = (body.get('client_name') or '').strip()
        client_contact_person = (body.get('client_contact_person') or '').strip()
        coordinator = (body.get('coordinator') or '').strip()
        requestor = (body.get('requestor') or '').strip()
        assigned_to = (body.get('assigned_to') or '').strip()
        job_description = (body.get('job_description') or '').strip()

        if not job_title or not skill or not client_name or not client_contact_person or not requestor or not job_description:
            return _err('Please fill in all required fields.')

        vals = {
            'client_name': _find_or_create_partner(client_name),
            'client_contact_person': client_contact_person,
            'coordinator_id': _find_or_create_employee(coordinator),
            'requestor_id': _find_or_create_employee(requestor),
            'assigned_to_id': _find_or_create_employee(assigned_to),
            'skill': skill,
            'job_title': job_title,
            'priority': body.get('priority') or '3',
            'status': body.get('status') or 'not_started',
            'job_description': job_description,
        }

        try:
            req_id = body.get('id')
            Requirement = request.env['hr.recruitment'].sudo()
            if req_id:
                rec = Requirement.browse(int(req_id))
                if not rec.exists():
                    return _err('Requirement not found.', 404)
                rec.write(vals)
            else:
                rec = Requirement.create(vals)
        except Exception as e:
            _logger.exception('requirement_save failed')
            return _err(str(e), 500)

        return _ok(
            requirement=_requirement_to_dict(rec, with_form=True),
            new_client=client_name,
            new_employees=[n for n in (coordinator, requestor, assigned_to) if n],
        )

    # -----------------------------------------------------------------------
    # Delete requirement
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements/delete', type='http', auth='user', methods=['POST'], csrf=False)
    def requirement_delete(self, **kw):
        body = _json_body()
        req_id = body.get('id')
        if not req_id:
            return _err('Missing id.')

        Requirement = request.env['hr.recruitment'].sudo()
        rec = Requirement.browse(int(req_id))
        if not rec.exists():
            return _err('Requirement not found.', 404)
        rec.unlink()
        return _ok()

    # -----------------------------------------------------------------------
    # Bulk-create requirements from uploaded job-spec documents
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements/upload', type='http', auth='user', methods=['POST'], csrf=True)
    def requirement_upload(self, **post):
        files = request.httprequest.files.getlist('files')
        if not files:
            return _err('No files uploaded.')

        default_person_id = _find_or_create_employee(request.env.user.name)
        Requirement = request.env['hr.recruitment'].sudo()
        Attachment = request.env['ir.attachment'].sudo()
        results = []

        for f in files:
            filename = f.filename or 'document'
            try:
                file_bytes = f.read()
                text = _extract_text(file_bytes, filename, f.mimetype or '')
                fields_out = _extract_requirement_fields(text, filename)

                vals = {
                    'client_name': _find_or_create_partner(fields_out['client_name'] or 'Unspecified Client'),
                    'client_contact_person': fields_out['client_contact_person'] or 'N/A',
                    'coordinator_id': default_person_id,
                    'requestor_id': default_person_id,
                    'skill': fields_out['skill'] or 'Not specified',
                    'job_title': fields_out['job_title'],
                    'job_description': fields_out['job_description'],
                }
                rec = Requirement.create(vals)
                Attachment.create({
                    'name': filename,
                    'datas': base64.b64encode(file_bytes).decode(),
                    'res_model': 'hr.recruitment',
                    'res_id': rec.id,
                })
                results.append({'filename': filename, 'ok': True, 'requirement': _requirement_to_dict(rec)})
            except Exception as e:
                _logger.exception('requirement_upload failed for %s', filename)
                results.append({'filename': filename, 'ok': False, 'error': str(e)})

        return _ok(results=results)

    # -----------------------------------------------------------------------
    # Requirement detail (details / candidates / notes)
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements/detail', type='http', auth='user', methods=['GET'])
    def requirement_detail(self, id=None, **kw):
        rec = request.env['hr.recruitment'].sudo().browse(int(id or 0))
        if not rec.exists():
            return _err('Requirement not found.', 404)

        return _ok(
            requirement=_requirement_to_dict(rec, with_form=True),
            candidates=[_candidate_to_dict(c) for c in rec.candidate_ids],
            notes=[_note_to_dict(n) for n in rec.note_ids],
        )

    # -----------------------------------------------------------------------
    # Add / edit candidate
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements/candidate/save', type='http', auth='user', methods=['POST'], csrf=False)
    def candidate_save(self, **kw):
        body = _json_body()
        requirement_id = int(body.get('requirement_id') or 0)
        name = (body.get('name') or '').strip()
        if not requirement_id:
            return _err('Missing requirement_id.')
        if not name:
            return _err('Candidate name is required.')

        requirement = request.env['hr.recruitment'].sudo().browse(requirement_id)
        if not requirement.exists():
            return _err('Requirement not found.', 404)

        def _float(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        coordinator = (body.get('coordinator') or '').strip()

        vals = {
            'requirement_id': requirement_id,
            'name': name,
            'current_salary': _float(body.get('current_salary')),
            'expected_salary': _float(body.get('expected_salary')),
            'email': (body.get('email') or '').strip(),
            'mobile': (body.get('mobile') or '').strip(),
            'current_location': (body.get('current_location') or '').strip(),
            'experience_years': _float(body.get('experience_years')),
            'notice_period': body.get('notice_period') or False,
            'interview_status': body.get('interview_status') or 'to_interview',
            'coordinator_id': _find_or_create_employee(coordinator),
            'closing_rate': _float(body.get('closing_rate')),
            'deployed': bool(body.get('deployed')),
        }

        file_b64 = body.get('resume_data')
        if file_b64:
            try:
                base64.b64decode(file_b64)
            except Exception:
                return _err('Invalid resume file data.')
            vals['resume_data'] = file_b64
            vals['resume_filename'] = body.get('resume_filename') or 'resume'

        try:
            Candidate = request.env['hr.recruitment.candidate'].sudo()
            cand_id = body.get('id')
            if cand_id:
                cand = Candidate.browse(int(cand_id))
                if not cand.exists():
                    return _err('Candidate not found.', 404)
                cand.write(vals)
            else:
                cand = Candidate.create(vals)
        except Exception as e:
            _logger.exception('candidate_save failed')
            return _err(str(e), 500)

        return _ok(candidate=_candidate_to_dict(cand), new_employees=[n for n in (coordinator,) if n])

    # -----------------------------------------------------------------------
    # Bulk-create candidates from uploaded resumes
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements/candidate/upload', type='http', auth='user', methods=['POST'], csrf=True)
    def candidate_upload(self, **post):
        requirement_id = int(post.get('requirement_id') or 0)
        if not requirement_id:
            return _err('Missing requirement_id.')
        requirement = request.env['hr.recruitment'].sudo().browse(requirement_id)
        if not requirement.exists():
            return _err('Requirement not found.', 404)

        files = request.httprequest.files.getlist('files')
        if not files:
            return _err('No files uploaded.')

        Candidate = request.env['hr.recruitment.candidate'].sudo()
        results = []

        for f in files:
            filename = f.filename or 'resume'
            try:
                file_bytes = f.read()
                parsed = _parse_resume(file_bytes, filename, f.mimetype or '')
                name = parsed['name'] if parsed['name'] and parsed['name'] != 'Unknown' else os.path.splitext(filename)[0]

                vals = {
                    'requirement_id': requirement_id,
                    'name': name,
                    'email': parsed['email'],
                    'mobile': parsed['phone'],
                    'experience_years': parsed['experience'],
                    'interview_status': 'to_interview',
                    'resume_data': base64.b64encode(file_bytes).decode(),
                    'resume_filename': filename,
                }
                cand = Candidate.create(vals)
                results.append({'filename': filename, 'ok': True, 'candidate': _candidate_to_dict(cand)})
            except Exception as e:
                _logger.exception('candidate_upload failed for %s', filename)
                results.append({'filename': filename, 'ok': False, 'error': str(e)})

        return _ok(results=results)

    # -----------------------------------------------------------------------
    # Work notes
    # -----------------------------------------------------------------------
    @http.route('/hrsd/recruitment/requirements/note/add', type='http', auth='user', methods=['POST'], csrf=False)
    def note_add(self, **kw):
        body = _json_body()
        requirement_id = int(body.get('requirement_id') or 0)
        text = (body.get('body') or '').strip()
        if not requirement_id:
            return _err('Missing requirement_id.')
        if not text:
            return _err('Comment cannot be empty.')

        requirement = request.env['hr.recruitment'].sudo().browse(requirement_id)
        if not requirement.exists():
            return _err('Requirement not found.', 404)

        note = request.env['hr.recruitment.note'].sudo().create({
            'requirement_id': requirement_id,
            'author_id': request.env.user.id,
            'body': text,
        })
        return _ok(note=_note_to_dict(note))
