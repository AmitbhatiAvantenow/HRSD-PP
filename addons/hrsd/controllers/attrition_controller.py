import json
from datetime import date, timedelta
from collections import defaultdict

from markupsafe import Markup
from odoo import http
from odoo.http import request

from .controllers import get_hrsd_branding


# ---------------------------------------------------------------------------
# Risk scoring helpers
# ---------------------------------------------------------------------------

_WEIGHTS = {
    'tenure':     0.25,
    'salary':     0.25,
    'leave':      0.15,
    'age':        0.10,
    'contract':   0.10,
    'attendance': 0.10,
    'skills':     0.05,
}

_FACTOR_LABELS = {
    'tenure':     'Tenure Pattern',
    'salary':     'Compensation Gap',
    'leave':      'Leave Behaviour',
    'age':        'Career Stage',
    'contract':   'Contract Type',
    'attendance': 'Attendance Rate',
    'skills':     'Skills Growth',
}

_RECOMMENDATIONS = {
    'tenure': {
        'high': "Schedule a stay-interview to understand the employee's long-term goals and map a growth path within the organisation.",
        'low':  "Provide structured onboarding support — new hires are statistically at higher attrition risk in the first 12 months.",
    },
    'salary': {
        'high': "Benchmark compensation against current market data. A pay-review conversation could significantly reduce flight risk.",
        'low':  "Salary is competitive. Consider recognising performance through equity, bonuses, or career-level promotions.",
    },
    'leave': {
        'high': "High leave usage may signal burnout or disengagement. Schedule a wellbeing check-in and review workload distribution.",
        'low':  "Leave patterns are healthy. Ensure employees are encouraged to take time off to avoid future burnout.",
    },
    'age': {
        'high': "Early-career employees explore options frequently. Offer clear career ladders, mentors, and stretch assignments.",
        'low':  "Experienced employees value stability and recognition. Explore senior advisory or mentoring role opportunities.",
    },
    'contract': {
        'high': "Consider converting contractors to permanent roles to boost loyalty and reduce overhead of repeated rehiring.",
        'low':  "Permanent contract employees show higher engagement. Reinforce their long-term growth plan regularly.",
    },
    'attendance': {
        'high': "Low attendance often precedes resignation. Conduct a confidential one-to-one to identify underlying concerns.",
        'low':  "Strong attendance indicates engagement. Acknowledge consistent dedication publicly or through peer recognition.",
    },
    'skills': {
        'high': "No logged skills may indicate a lack of development investment. Enrol the employee in a learning programme.",
        'low':  "Active skill-builders are generally more engaged. Continue funding L&D to retain top performers.",
    },
}


def _tenure_score(contract_start, today):
    if not contract_start:
        return 40
    months = max(0, (today - contract_start).days / 30.44)
    if months < 6:
        return 85
    if months < 12:
        return 65
    if months < 24:
        return 50
    if months < 60:
        return 30
    if months < 120:
        return 22
    return 14


def _age_score(birthday, today):
    if not birthday:
        return 40
    age = (today - birthday).days / 365.25
    if age < 25:
        return 75
    if age < 30:
        return 60
    if age < 40:
        return 38
    if age < 50:
        return 22
    return 14


def _salary_score(wage, dept_avg):
    if not dept_avg or not wage:
        return 40
    ratio = wage / dept_avg
    if ratio < 0.80:
        return 88
    if ratio < 0.90:
        return 68
    if ratio < 1.00:
        return 45
    if ratio < 1.15:
        return 20
    return 12


def _leave_score(sick_days, total_days):
    if total_days > 20:
        return 75
    if total_days > 12:
        return 55
    if sick_days > 6:
        return 60
    if sick_days > 3:
        return 40
    if total_days > 6:
        return 30
    return 18


def _contract_score(contract_type_name):
    name = (contract_type_name or '').lower()
    if any(k in name for k in ('contractor', 'freelance', 'temporary', 'temp', 'fixed')):
        return 80
    if 'part' in name:
        return 55
    if not name:
        return 45
    return 18


def _attendance_score(rate):
    if rate is None:
        return 38
    if rate < 0.80:
        return 82
    if rate < 0.88:
        return 58
    if rate < 0.94:
        return 32
    return 14


def _skills_score(skill_count):
    if skill_count == 0:
        return 62
    if skill_count < 3:
        return 38
    if skill_count < 6:
        return 22
    return 12


def _build_recommendations(factors, risk_level):
    lines = []
    # top 3 factors by weighted contribution
    ranked = sorted(factors.keys(), key=lambda k: factors[k] * _WEIGHTS[k], reverse=True)
    for key in ranked[:3]:
        score = factors[key]
        bucket = 'high' if score >= 50 else 'low'
        rec = _RECOMMENDATIONS.get(key, {}).get(bucket)
        if rec:
            lines.append(rec)
    return lines


def _compute_risk(emp, today, dept_avg_wages, leave_stats, att_stats):
    # --- individual factor scores ----------------------------------------
    contract_start = None
    try:
        contract_start = emp.contract_date_start
    except Exception:
        pass
    if not contract_start and emp.create_date:
        contract_start = emp.create_date.date()

    factors = {
        'tenure':     _tenure_score(contract_start, today),
        'age':        _age_score(emp.birthday, today),
        'salary':     _salary_score(
            getattr(emp, 'contract_wage', 0) or 0,
            dept_avg_wages.get(emp.department_id.id, 0),
        ),
        'leave':      _leave_score(*leave_stats.get(emp.id, (0, 0))),
        'contract':   _contract_score(
            emp.contract_type_id.name if getattr(emp, 'contract_type_id', False) and emp.contract_type_id else ''
        ),
        'attendance': _attendance_score(att_stats.get(emp.id)),
        'skills':     _skills_score(len(emp.employee_skill_ids) if hasattr(emp, 'employee_skill_ids') else 0),
    }

    risk_score = round(sum(factors[k] * _WEIGHTS[k] for k in factors), 1)

    if risk_score >= 70:
        risk_level = 'critical'
    elif risk_score >= 50:
        risk_level = 'high'
    elif risk_score >= 30:
        risk_level = 'medium'
    else:
        risk_level = 'low'

    top_factor = max(factors, key=lambda k: factors[k] * _WEIGHTS[k])

    recs = _build_recommendations(factors, risk_level)

    tenure_months = 0
    if contract_start:
        tenure_months = max(0, int((today - contract_start).days / 30.44))

    age_val = None
    if emp.birthday:
        age_val = int((today - emp.birthday).days / 365.25)

    return {
        'risk_score':        risk_score,
        'risk_level':        risk_level,
        'top_factor':        _FACTOR_LABELS[top_factor],
        'tenure_factor':     factors['tenure'],
        'age_factor':        factors['age'],
        'salary_factor':     factors['salary'],
        'leave_factor':      factors['leave'],
        'contract_factor':   factors['contract'],
        'attendance_factor': factors['attendance'],
        'skills_factor':     factors['skills'],
        'recommendations':   '\n'.join(recs),
        'tenure_months':     tenure_months,
        'age':               age_val,
    }


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _dept_avg_wages(employees):
    dept_wages = defaultdict(list)
    for emp in employees:
        wage = getattr(emp, 'contract_wage', 0) or 0
        if wage and emp.department_id:
            dept_wages[emp.department_id.id].append(wage)
    return {did: (sum(wages) / len(wages)) for did, wages in dept_wages.items() if wages}


def _leave_statistics(env, employee_ids, year_start, today):
    """Returns {emp_id: (sick_days, total_days)} for current year."""
    result = {}
    try:
        Leave = env['hr.leave.allocation'].sudo()
        # Use hr.leave (time-off requests)
        LeaveReq = env['hr.leave'].sudo()
        leaves = LeaveReq.search([
            ('employee_id', 'in', employee_ids),
            ('state', '=', 'validate'),
            ('date_from', '>=', year_start),
            ('date_from', '<=', today),
        ])
        sick_types = set()
        try:
            lt_env = env['hr.leave.type'].sudo()
            sick_lt = lt_env.search([('name', 'ilike', 'sick')])
            sick_types = {lt.id for lt in sick_lt}
        except Exception:
            pass

        for leave in leaves:
            eid = leave.employee_id.id
            if eid not in result:
                result[eid] = [0, 0]
            days = leave.number_of_days or 0
            result[eid][1] += days
            if leave.holiday_status_id.id in sick_types:
                result[eid][0] += days
    except Exception:
        pass
    return {eid: tuple(v) for eid, v in result.items()}


def _attendance_statistics(env, employee_ids, ninety_days_ago, today):
    """Returns {emp_id: attendance_rate (0-1)} based on last 90 days."""
    result = {}
    try:
        Att = env['hr.attendance'].sudo()
        records = Att.search([
            ('employee_id', 'in', employee_ids),
            ('check_in', '>=', ninety_days_ago),
            ('check_in', '<=', today),
        ])
        emp_days = defaultdict(set)
        for rec in records:
            emp_days[rec.employee_id.id].add(rec.check_in.date())

        # working days in 90-day window (Mon-Fri only, rough estimate)
        working_days = sum(
            1 for i in range(90)
            if (today - timedelta(days=i)).weekday() < 5
        )

        for eid in employee_ids:
            days_present = len(emp_days.get(eid, set()))
            result[eid] = round(days_present / working_days, 3) if working_days else None
    except Exception:
        pass
    return result


def _trend_data(env, today):
    """Last 6 monthly snapshot averages."""
    try:
        Snap = env['hr.attrition.snapshot'].sudo()
        trend = []
        for m in range(5, -1, -1):
            # first day of month m months ago
            month_offset = today.month - m
            year = today.year + (month_offset - 1) // 12
            month = ((month_offset - 1) % 12) + 1
            m_start = date(year, month, 1)
            if month == 12:
                m_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = date(year, month + 1, 1) - timedelta(days=1)
            snaps = Snap.search([
                ('snapshot_date', '>=', m_start),
                ('snapshot_date', '<=', m_end),
            ])
            if snaps:
                avg = round(sum(s.risk_score for s in snaps) / len(snaps), 1)
                trend.append({'label': m_start.strftime('%b %Y'), 'avg': avg, 'count': len(snaps)})
        return trend
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class AttritionController(http.Controller):

    @http.route('/hrsd/attrition', type='http', auth='user', website=False, sitemap=False)
    def attrition_page(self, **kw):
        env = request.env
        today = date.today()
        year_start = today.replace(month=1, day=1)
        ninety_ago = today - timedelta(days=90)

        employees = env['hr.employee'].sudo().search([('active', '=', True)])
        employee_ids = employees.ids

        # --- load latest HR assessment per employee -----------------------
        assessments = {}
        try:
            Assess = env['hr.attrition.assessment'].sudo()
            all_a = Assess.search([('employee_id', 'in', employee_ids)],
                                   order='assessment_date desc')
            for a in all_a:
                eid = a.employee_id.id
                if eid not in assessments:
                    assessments[eid] = a
        except Exception:
            pass

        # --- load today's cached snapshots (read-only fast path) -----------
        Snap = None
        cached_snaps = {}       # emp_id -> snapshot record (already computed today)
        missing_emp_ids = set(employee_ids)
        try:
            Snap = env['hr.attrition.snapshot'].sudo()
            todays = Snap.search([('snapshot_date', '=', today),
                                   ('employee_id', 'in', employee_ids)])
            for s in todays:
                cached_snaps[s.employee_id.id] = s
            missing_emp_ids = set(employee_ids) - set(cached_snaps.keys())
        except Exception:
            pass

        # --- compute stats only for employees without today's snapshot ------
        dept_avgs = {}
        leave_stats = {}
        att_stats = {}
        if missing_emp_ids:
            dept_avgs   = _dept_avg_wages(employees)
            leave_stats = _leave_statistics(env, employee_ids, year_start, today)
            att_stats   = _attendance_statistics(env, employee_ids, ninety_ago, today)

        emp_results = []
        dist = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        dept_scores = defaultdict(list)

        # Map employee objects for quick lookup
        emp_map = {emp.id: emp for emp in employees}

        for emp in employees:
            dept_name = emp.department_id.name or 'No Department'
            avatar_url = f'/web/image/hr.employee/{emp.id}/image_1920' if emp.image_1920 else None

            if emp.id in cached_snaps:
                # --- use cached snapshot (no DB write) ---------------------
                s = cached_snaps[emp.id]
                risk_score = s.risk_score
                level      = s.risk_level or 'low'
                top_factor = s.top_factor or ''
                recs       = (s.recommendations or '').split('\n') if s.recommendations else []
                factors    = {
                    'Tenure':     s.tenure_factor,
                    'Comp. Gap':  s.salary_factor,
                    'Leave':      s.leave_factor,
                    'Career Age': s.age_factor,
                    'Contract':   s.contract_factor,
                    'Attendance': s.attendance_factor,
                    'Skills':     s.skills_factor,
                }
                contract_start = None
                try:
                    contract_start = emp.contract_date_start
                except Exception:
                    pass
                if not contract_start and emp.create_date:
                    contract_start = emp.create_date.date()
                tenure_months = max(0, int((today - contract_start).days / 30.44)) if contract_start else 0
                age_val = int((today - emp.birthday).days / 365.25) if emp.birthday else None
            else:
                # --- fresh computation + INSERT only (no UPDATE) -----------
                risk       = _compute_risk(emp, today, dept_avgs, leave_stats, att_stats)
                level      = risk['risk_level']
                risk_score = risk['risk_score']
                top_factor = risk['top_factor']
                recs       = risk['recommendations'].split('\n') if risk['recommendations'] else []
                factors    = {
                    'Tenure':     risk['tenure_factor'],
                    'Comp. Gap':  risk['salary_factor'],
                    'Leave':      risk['leave_factor'],
                    'Career Age': risk['age_factor'],
                    'Contract':   risk['contract_factor'],
                    'Attendance': risk['attendance_factor'],
                    'Skills':     risk['skills_factor'],
                }
                tenure_months = risk['tenure_months']
                age_val       = risk['age']

                if Snap is not None:
                    try:
                        Snap.create({
                            'employee_id':        emp.id,
                            'snapshot_date':      today,
                            'risk_score':         risk_score,
                            'risk_level':         level,
                            'tenure_factor':      risk['tenure_factor'],
                            'age_factor':         risk['age_factor'],
                            'salary_factor':      risk['salary_factor'],
                            'leave_factor':       risk['leave_factor'],
                            'contract_factor':    risk['contract_factor'],
                            'attendance_factor':  risk['attendance_factor'],
                            'skills_factor':      risk['skills_factor'],
                            'top_factor':         top_factor,
                            'recommendations':    risk['recommendations'],
                        })
                    except Exception:
                        # concurrent INSERT hit the unique constraint — safe to ignore
                        pass

            # --- blend with HR assessment if available --------------------
            a = assessments.get(emp.id)
            if a:
                blended = round(0.5 * risk_score + 0.5 * a.assessment_risk_score, 1)
                assessed = True
                assessed_date = a.assessment_date.strftime('%d %b %Y') if a.assessment_date else ''
                assess_answers = {
                    'q_engagement':          a.q_engagement,
                    'q_salary_satisfaction': a.q_salary_satisfaction,
                    'q_career_growth':       a.q_career_growth,
                    'q_manager_relation':    a.q_manager_relation,
                    'q_retention_confidence': a.q_retention_confidence,
                    'q_job_hunting':         a.q_job_hunting,
                    'q_recent_promotion':    a.q_recent_promotion,
                    'q_burnout_risk':        a.q_burnout_risk,
                    'notes':                 a.notes or '',
                    'assessment_risk_score': a.assessment_risk_score,
                    'assessed_by':           a.assessed_by.name or '',
                }
            else:
                blended      = risk_score
                assessed     = False
                assessed_date = ''
                assess_answers = {}

            # recalculate level from blended score
            if blended >= 70:
                level = 'critical'
            elif blended >= 50:
                level = 'high'
            elif blended >= 30:
                level = 'medium'
            else:
                level = 'low'

            dist[level] += 1
            dept_scores[dept_name].append(blended)

            emp_results.append({
                'id':            emp.id,
                'name':          emp.name or '',
                'dept':          dept_name,
                'job':           emp.job_title or emp.job_id.name or '',
                'tenure_months': tenure_months,
                'age':           age_val,
                'risk_score':    blended,
                'auto_score':    risk_score,
                'risk_level':    level,
                'top_factor':    top_factor,
                'avatar':        avatar_url,
                'factors':       factors,
                'recommendations': recs,
                'assessed':      assessed,
                'assessed_date': assessed_date,
                'assess_answers': assess_answers,
            })

        emp_results.sort(key=lambda e: e['risk_score'], reverse=True)

        # --- department aggregates ----------------------------------------
        by_dept = sorted([
            {
                'name':       dept,
                'avg_score':  round(sum(scores) / len(scores), 1),
                'count':      len(scores),
                'high_count': sum(1 for s in scores if s >= 50),
            }
            for dept, scores in dept_scores.items()
        ], key=lambda d: d['avg_score'], reverse=True)[:10]

        # --- KPIs ---------------------------------------------------------
        total = len(emp_results)
        high_critical = dist['high'] + dist['critical']
        at_risk = dist['medium'] + high_critical
        avg_score = round(sum(e['risk_score'] for e in emp_results) / total, 1) if total else 0

        kpis = {
            'total':        total,
            'at_risk':      at_risk,
            'high_critical': high_critical,
            'avg_score':    avg_score,
            'safe':         dist['low'],
        }

        trend = _trend_data(env, today)

        page_data = {
            'kpis':       kpis,
            'dist':       dist,
            'by_dept':    by_dept,
            'trend':      trend,
            'employees':  emp_results,
            'computed_at': today.strftime('%d %b %Y'),
        }

        return request.render('hrsd.attrition_page', {
            'page_data_json': Markup(json.dumps(page_data)),
            'computed_at':    today.strftime('%d %b %Y'),
            'brand':          get_hrsd_branding(env),
        })

    # -----------------------------------------------------------------------
    # Assessment API
    # -----------------------------------------------------------------------

    @http.route('/hrsd/attrition/assess/save', type='http', auth='user',
                methods=['POST'], csrf=False)
    def assess_save(self, **post):
        def _json(data, status=200):
            return request.make_response(
                json.dumps(data),
                headers=[('Content-Type', 'application/json')],
                status=status,
            )

        try:
            emp_id = int(post.get('employee_id', 0))
            if not emp_id:
                return _json({'ok': False, 'error': 'Missing employee_id'}, 400)

            env = request.env
            emp = env['hr.employee'].sudo().browse(emp_id)
            if not emp.exists():
                return _json({'ok': False, 'error': 'Employee not found'}, 404)

            def _int(key, default=3):
                try:
                    v = int(post.get(key, default))
                    return max(1, min(5, v))
                except Exception:
                    return default

            def _bool(key):
                return post.get(key, '').lower() in ('1', 'true', 'yes', 'on')

            vals = {
                'employee_id':           emp_id,
                'q_engagement':          _int('q_engagement'),
                'q_salary_satisfaction': _int('q_salary_satisfaction'),
                'q_career_growth':       _int('q_career_growth'),
                'q_manager_relation':    _int('q_manager_relation'),
                'q_retention_confidence': _int('q_retention_confidence'),
                'q_job_hunting':         _bool('q_job_hunting'),
                'q_recent_promotion':    _bool('q_recent_promotion'),
                'q_burnout_risk':        _bool('q_burnout_risk'),
                'notes':                 post.get('notes', '').strip(),
            }

            # Compute assessment score inline
            score = 50.0
            score -= (vals['q_engagement'] - 3) * 8.0
            score -= (vals['q_salary_satisfaction'] - 3) * 5.0
            score -= (vals['q_career_growth'] - 3) * 5.0
            score -= (vals['q_manager_relation'] - 3) * 3.0
            score -= (vals['q_retention_confidence'] - 3) * 10.0
            if vals['q_job_hunting']:   score += 25.0
            if vals['q_recent_promotion']: score -= 15.0
            if vals['q_burnout_risk']:  score += 10.0
            assess_score = max(0.0, min(100.0, round(score, 1)))
            vals['assessment_risk_score'] = assess_score

            Assess = env['hr.attrition.assessment'].sudo()
            Assess.create(vals)

            # Compute blended score (50% auto + 50% assessment)
            today = date.today()
            auto_score = 50.0
            try:
                Snap = env['hr.attrition.snapshot'].sudo()
                snap = Snap.search([('employee_id', '=', emp_id),
                                    ('snapshot_date', '=', today)], limit=1)
                if snap:
                    auto_score = snap.risk_score
            except Exception:
                pass

            blended = round(0.5 * auto_score + 0.5 * assess_score, 1)
            if blended >= 70:   level = 'critical'
            elif blended >= 50: level = 'high'
            elif blended >= 30: level = 'medium'
            else:               level = 'low'

            return _json({
                'ok':                True,
                'employee_id':       emp_id,
                'assess_score':      assess_score,
                'auto_score':        auto_score,
                'blended_score':     blended,
                'risk_level':        level,
                'assessed_date':     date.today().strftime('%d %b %Y'),
                'assessed_by':       request.env.user.name,
                'answers': {
                    'q_engagement':          vals['q_engagement'],
                    'q_salary_satisfaction': vals['q_salary_satisfaction'],
                    'q_career_growth':       vals['q_career_growth'],
                    'q_manager_relation':    vals['q_manager_relation'],
                    'q_retention_confidence': vals['q_retention_confidence'],
                    'q_job_hunting':         vals['q_job_hunting'],
                    'q_recent_promotion':    vals['q_recent_promotion'],
                    'q_burnout_risk':        vals['q_burnout_risk'],
                    'notes':                 vals['notes'],
                    'assessment_risk_score': assess_score,
                    'assessed_by':           request.env.user.name,
                },
            })

        except Exception as e:
            return _json({'ok': False, 'error': str(e)}, 500)
