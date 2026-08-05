import json
from collections import defaultdict
from datetime import date

from markupsafe import Markup
from odoo import http, fields
from odoo.http import request

from .controllers import get_hrsd_branding, require_hrsd_confidential_access


COMPETENCY_LABELS = {
    'communication': 'Communication',
    'teamwork': 'Teamwork & Collaboration',
    'problem_solving': 'Problem Solving',
    'leadership': 'Leadership',
    'technical_skills': 'Technical / Job Skills',
    'adaptability': 'Adaptability',
    'ownership': 'Ownership & Accountability',
    'quality': 'Quality of Work',
}

BAND_LABELS = {
    'outstanding': 'Outstanding',
    'exceeds': 'Exceeds Expectations',
    'meets': 'Meets Expectations',
    'below': 'Below Expectations',
    'unsatisfactory': 'Unsatisfactory',
}

STATE_LABELS = {
    'draft': 'Draft',
    'self_assessment': 'Self-Assessment',
    'manager_review': 'Manager Review',
    'calibration': 'Calibration',
    'completed': 'Completed',
    'cancelled': 'Cancelled',
}

PERF_BUCKET = {
    'outstanding': 'high', 'exceeds': 'high',
    'meets': 'medium',
    'below': 'low', 'unsatisfactory': 'low',
}


def _json_response(data, status=200):
    return request.make_response(
        json.dumps(data),
        headers=[('Content-Type', 'application/json')],
        status=status,
    )


def _appraisal_to_dict(a):
    emp = a.employee_id
    avatar_url = f'/web/image/hr.employee/{emp.id}/image_1920' if emp.image_1920 else None

    goals = [{
        'id': g.id,
        'name': g.name,
        'description': g.description or '',
        'category': g.category,
        'weight': g.weight,
        'target_value': g.target_value or '',
        'self_progress': g.self_progress,
        'manager_progress': g.manager_progress,
        'status': g.status,
    } for g in a.goal_ids]

    comps = [{
        'id': c.id,
        'name': c.name,
        'name_label': COMPETENCY_LABELS.get(c.name, c.name),
        'self_score': c.self_score,
        'manager_score': c.manager_score,
        'self_comments': c.self_comments or '',
        'manager_comments': c.manager_comments or '',
    } for c in a.competency_ids]

    feedback = [{
        'reviewer': f.reviewer_id.name or 'Anonymous',
        'relation': f.relation,
        'rating': f.rating,
        'comments': f.comments or '',
        'date': f.submitted_date.strftime('%d %b %Y') if f.submitted_date else '',
    } for f in a.feedback_ids]

    return {
        'id': a.id,
        'employee_id': emp.id,
        'name': emp.name or '',
        'job': emp.job_title or emp.job_id.name or '',
        'dept': a.department_id.name or 'No Department',
        'avatar': avatar_url,
        'manager': a.manager_id.name or '',
        'cycle_type': a.cycle_type,
        'period_start': a.period_start.strftime('%d %b %Y') if a.period_start else '',
        'period_end': a.period_end.strftime('%d %b %Y') if a.period_end else '',
        'deadline_date': a.deadline_date.strftime('%d %b %Y') if a.deadline_date else '',
        'state': a.state,
        'state_label': STATE_LABELS.get(a.state, a.state),
        'is_overdue': a.is_overdue,
        'self_score': a.overall_self_score,
        'manager_score': a.overall_manager_score,
        'overall_score': a.overall_score,
        'performance_band': a.performance_band,
        'band_label': BAND_LABELS.get(a.performance_band, a.performance_band),
        'potential': a.potential,
        'nine_box_label': a.nine_box_label,
        'goals': goals,
        'competencies': comps,
        'feedback': feedback,
        'strengths': a.strengths or '',
        'areas_of_improvement': a.areas_of_improvement or '',
        'development_plan': a.development_plan or '',
        'employee_comments': a.employee_comments or '',
        'manager_comments': a.manager_comments or '',
    }


class AppraisalController(http.Controller):

    @http.route('/hrsd/appraisal', type='http', auth='user', website=False, sitemap=False)
    def appraisal_page(self, **kw):
        require_hrsd_confidential_access()
        env = request.env
        today = date.today()

        Appraisal = env['hr.appraisal'].sudo()
        appraisals = Appraisal.search([('state', '!=', 'cancelled')])

        results = [_appraisal_to_dict(a) for a in appraisals]
        results.sort(key=lambda r: r['overall_score'], reverse=True)

        dist = defaultdict(int)
        dept_scores = defaultdict(list)
        nine_box = defaultdict(int)
        completed = 0
        in_progress = 0
        overdue = 0

        for a in appraisals:
            dist[a.performance_band] += 1
            dept_scores[a.department_id.name or 'No Department'].append(a.overall_score)
            perf = PERF_BUCKET.get(a.performance_band, 'medium')
            nine_box[f'{perf}_{a.potential or "medium"}'] += 1
            if a.state == 'completed':
                completed += 1
            elif a.state in ('self_assessment', 'manager_review', 'calibration'):
                in_progress += 1
            if a.is_overdue:
                overdue += 1

        total = len(appraisals)
        avg_score = round(sum(a.overall_score for a in appraisals) / total, 1) if total else 0

        by_dept = sorted([
            {
                'name': dept,
                'avg_score': round(sum(scores) / len(scores), 1),
                'count': len(scores),
            }
            for dept, scores in dept_scores.items()
        ], key=lambda d: d['avg_score'], reverse=True)[:10]

        page_data = {
            'kpis': {
                'total': total,
                'completed': completed,
                'in_progress': in_progress,
                'overdue': overdue,
                'avg_score': avg_score,
            },
            'dist': {
                'outstanding': dist.get('outstanding', 0),
                'exceeds': dist.get('exceeds', 0),
                'meets': dist.get('meets', 0),
                'below': dist.get('below', 0),
                'unsatisfactory': dist.get('unsatisfactory', 0),
            },
            'nine_box': dict(nine_box),
            'by_dept': by_dept,
            'appraisals': results,
            'computed_at': today.strftime('%d %b %Y'),
        }

        manage_action = env.ref('hrsd.action_hr_appraisal', raise_if_not_found=False)
        manage_url = f'/odoo/action-{manage_action.id}' if manage_action else '/odoo/action-hrsd'

        return request.render('hrsd.appraisal_page', {
            'page_data_json': Markup(json.dumps(page_data)),
            'computed_at': today.strftime('%d %b %Y'),
            'manage_url': manage_url,
            'brand': get_hrsd_branding(env),
        })

    # -----------------------------------------------------------------------
    # Kick off self-assessment stage
    # -----------------------------------------------------------------------

    @http.route('/hrsd/appraisal/start', type='http', auth='user',
                methods=['POST'], csrf=False)
    def start_review(self, **kw):
        require_hrsd_confidential_access()
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or '{}')
            appraisal_id = int(payload.get('appraisal_id', 0))
            if not appraisal_id:
                return _json_response({'ok': False, 'error': 'Missing appraisal_id'}, 400)

            appraisal = request.env['hr.appraisal'].sudo().browse(appraisal_id)
            if not appraisal.exists():
                return _json_response({'ok': False, 'error': 'Appraisal not found'}, 404)

            appraisal.action_start_self_assessment()
            return _json_response({'ok': True, 'appraisal': _appraisal_to_dict(appraisal)})
        except Exception as e:
            return _json_response({'ok': False, 'error': str(e)}, 500)

    # -----------------------------------------------------------------------
    # Self-assessment API
    # -----------------------------------------------------------------------

    @http.route('/hrsd/appraisal/self-assess/save', type='http', auth='user',
                methods=['POST'], csrf=False)
    def self_assess_save(self, **kw):
        require_hrsd_confidential_access()
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or '{}')
            appraisal_id = int(payload.get('appraisal_id', 0))
            if not appraisal_id:
                return _json_response({'ok': False, 'error': 'Missing appraisal_id'}, 400)

            env = request.env
            appraisal = env['hr.appraisal'].sudo().browse(appraisal_id)
            if not appraisal.exists():
                return _json_response({'ok': False, 'error': 'Appraisal not found'}, 404)

            for g in payload.get('goals', []):
                goal = appraisal.goal_ids.filtered(lambda x: x.id == int(g.get('id', 0)))
                if goal:
                    progress = max(0, min(100, int(g.get('self_progress', 0))))
                    goal.write({'self_progress': progress})

            for c in payload.get('competencies', []):
                comp = appraisal.competency_ids.filtered(lambda x: x.id == int(c.get('id', 0)))
                if comp:
                    score = max(1, min(5, int(c.get('self_score', 3))))
                    comp.write({'self_score': score})

            appraisal.write({
                'state': 'manager_review',
                'self_assessment_date': fields.Datetime.now(),
                'employee_comments': (payload.get('comments') or '').strip(),
            })
            appraisal.message_post(body='Employee submitted their self-assessment via the portal dashboard.')

            return _json_response({'ok': True, 'appraisal': _appraisal_to_dict(appraisal)})
        except Exception as e:
            return _json_response({'ok': False, 'error': str(e)}, 500)

    # -----------------------------------------------------------------------
    # Manager review API
    # -----------------------------------------------------------------------

    @http.route('/hrsd/appraisal/manager-review/save', type='http', auth='user',
                methods=['POST'], csrf=False)
    def manager_review_save(self, **kw):
        require_hrsd_confidential_access()
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or '{}')
            appraisal_id = int(payload.get('appraisal_id', 0))
            if not appraisal_id:
                return _json_response({'ok': False, 'error': 'Missing appraisal_id'}, 400)

            env = request.env
            appraisal = env['hr.appraisal'].sudo().browse(appraisal_id)
            if not appraisal.exists():
                return _json_response({'ok': False, 'error': 'Appraisal not found'}, 404)

            for g in payload.get('goals', []):
                goal = appraisal.goal_ids.filtered(lambda x: x.id == int(g.get('id', 0)))
                if goal:
                    progress = max(0, min(100, int(g.get('manager_progress', 0))))
                    vals = {'manager_progress': progress}
                    status = g.get('status')
                    if status:
                        vals['status'] = status
                    goal.write(vals)

            for c in payload.get('competencies', []):
                comp = appraisal.competency_ids.filtered(lambda x: x.id == int(c.get('id', 0)))
                if comp:
                    score = max(1, min(5, int(c.get('manager_score', 3))))
                    comp.write({'manager_score': score})

            potential = payload.get('potential')
            if potential not in ('low', 'medium', 'high'):
                potential = 'medium'

            now = fields.Datetime.now()
            appraisal.write({
                'state': 'completed',
                'manager_review_date': now,
                'completion_date': now,
                'potential': potential,
                'strengths': (payload.get('strengths') or '').strip(),
                'areas_of_improvement': (payload.get('areas_of_improvement') or '').strip(),
                'development_plan': (payload.get('development_plan') or '').strip(),
                'manager_comments': (payload.get('manager_comments') or '').strip(),
            })
            appraisal.message_post(body='Manager completed the review via the portal dashboard.')

            return _json_response({'ok': True, 'appraisal': _appraisal_to_dict(appraisal)})
        except Exception as e:
            return _json_response({'ok': False, 'error': str(e)}, 500)
