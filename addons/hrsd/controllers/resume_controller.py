import base64
import io
import json
import logging
import os
import re
import csv

from odoo import http
from odoo.http import request

from .controllers import get_hrsd_branding

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Comprehensive skills dictionary for matching
# ---------------------------------------------------------------------------
SKILLS = {
    # Programming languages
    'python','java','javascript','typescript','c++','c#','php','ruby','go','rust',
    'swift','kotlin','scala','r programming','matlab','perl','bash','shell','powershell',
    'vba','cobol','fortran','dart','lua','groovy',
    # Web / Frontend
    'react','angular','vue','next.js','nuxt','svelte','jquery','html','css','sass',
    'tailwind','bootstrap','webpack','vite','gatsby','redux',
    # Backend / Frameworks
    'django','flask','fastapi','spring','laravel','rails','express','nestjs','asp.net',
    'node.js','graphql','rest api','soap','microservices',
    # Data / ML / AI
    'pandas','numpy','scikit-learn','tensorflow','pytorch','keras','opencv','nltk','spacy',
    'tableau','power bi','looker','excel','google analytics','data analysis',
    'machine learning','deep learning','data science','statistics','r',
    'hadoop','spark','kafka','airflow','dbt','snowflake','databricks',
    # Databases
    'mysql','postgresql','mongodb','redis','elasticsearch','oracle','sqlite',
    'dynamodb','cassandra','sql server','firebase','supabase','sql',
    # Cloud & DevOps
    'aws','azure','gcp','google cloud','docker','kubernetes','jenkins','gitlab',
    'github actions','terraform','ansible','linux','nginx','apache','ci/cd',
    'devops','site reliability','cloudformation','helm',
    # HR & Business
    'hris','sap','oracle hcm','workday','successfactors','odoo','zoho hr','bamboohr',
    'recruitment','payroll','performance management','talent acquisition','onboarding',
    'employee relations','learning & development','compensation & benefits',
    'labour law','hr analytics','workforce planning','kpi','okr',
    # Finance / Accounting
    'accounting','financial analysis','budgeting','forecasting','quickbooks',
    'sap fi','tally','ifrs','gaap','auditing','tax','cost accounting',
    # Marketing / Sales
    'digital marketing','seo','sem','social media','content marketing','email marketing',
    'hubspot','salesforce','crm','google ads','facebook ads','copywriting',
    # Design
    'figma','adobe xd','photoshop','illustrator','sketch','ui/ux','canva','indesign',
    # Project Management
    'agile','scrum','kanban','jira','confluence','ms project','pmp','prince2',
    'project management','product management','stakeholder management',
    # Soft Skills
    'leadership','communication','teamwork','problem solving','analytical thinking',
    'presentation','negotiation','time management','mentoring','coaching',
    'critical thinking','decision making','conflict resolution',
    # Office / General
    'ms office','microsoft office','microsoft excel','microsoft word','powerpoint',
    'g suite','google workspace','erp','crm','zendesk',
    # ITSM / ServiceNow / IT Operations
    'itsm','itom','itil','servicenow','hrsd','cmdb','discovery','orchestration',
    'csa','cis','cdm','csdm','itbm','grc','itsm','spa','service catalog',
    'incident management','change management','problem management','asset management',
    'service mapping','event management','virtual agent','performance analytics',
    'mid server','rest','soap integration','flow designer','business rules',
    'client scripts','ui policies','ui actions','update sets','ldap',
    'active directory','sso','oauth','saml','api integration','web services',
    'cab','sla','slo','kpi reporting','workflow automation',
}

EDUCATION_PATTERNS = [
    (r'\bph\.?\s*d\b|\bdoctorate?\b|\bdoctoral\b',                       'phd'),
    (r'\bm\.?\s*b\.?\s*a\b|\bm\.?\s*s\b|\bmaster(?:s|\'s)?\b|\bm\.?\s*tech\b|\bm\.?\s*e\b', 'master'),
    (r'\bb\.?\s*s\b|\bb\.?\s*a\b|\bb\.?\s*tech\b|\bb\.?\s*e\b|\bbachelor(?:s|\'s)?\b|\bundergrad', 'bachelor'),
    (r'\bhigh\s+school\b|\bhsc\b|\bssc\b|\bdiploma\b|\ba[\s-]?levels?\b', 'high_school'),
]

EXPERIENCE_RE = [
    r'(\d+)\+?\s+years?\s+(?:of\s+)?(?:work\s+)?(?:experience|exp)',
    r'(\d+)\+?\s+yrs?\s+(?:of\s+)?(?:work\s+)?(?:experience|exp)',
    r'experience\s*(?:of\s*)?(\d+)\+?\s+years?',
    r'(\d+)\+?\s+years?\s+in\s+\w',
]

DATE_RANGE_RE = re.compile(
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[,\s]+(\d{4})'
    r'\s*[-–—to]+\s*'
    r'(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[,\s]+)?(\d{4}|present|current|now)',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Package availability check
# ---------------------------------------------------------------------------
def _check_imports():
    missing = []
    for pkg, imp in [
        ('pdfminer.six',  'pdfminer.high_level'),
        ('python-docx',   'docx'),
        ('rapidfuzz',     'rapidfuzz'),
        ('scikit-learn',  'sklearn'),
    ]:
        try:
            __import__(imp)
        except ImportError:
            missing.append(pkg)
    return missing


# ---------------------------------------------------------------------------
# JSON request helper
# ---------------------------------------------------------------------------
def _json_body():
    """Parse JSON body from an http-type POST request."""
    try:
        data = request.httprequest.data
        if data:
            return json.loads(data.decode('utf-8'))
    except Exception:
        pass
    return {}


def _ok(**kwargs):
    d = {'ok': True}
    d.update(kwargs)
    return request.make_response(
        json.dumps(d),
        headers=[('Content-Type', 'application/json')]
    )


def _err(msg, status=400):
    return request.make_response(
        json.dumps({'ok': False, 'error': msg}),
        headers=[('Content-Type', 'application/json')],
        status=status
    )


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def _extract_text(file_bytes, filename, mimetype=''):
    ext = os.path.splitext(filename or '')[1].lower()
    is_pdf  = mimetype == 'application/pdf' or ext == '.pdf'
    is_docx = mimetype in (
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ) or ext in ('.docx', '.doc')

    if is_pdf:
        try:
            from pdfminer.high_level import extract_text
            return extract_text(io.BytesIO(file_bytes)) or ''
        except Exception as e:
            _logger.warning("PDF extraction failed: %s", e)
            return ''
    if is_docx:
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            return '\n'.join(p.text for p in doc.paragraphs) or ''
        except Exception as e:
            _logger.warning("DOCX extraction failed: %s", e)
            return ''
    try:
        return file_bytes.decode('utf-8', errors='replace')
    except Exception:
        return ''


# ---------------------------------------------------------------------------
# Resume parsing
# ---------------------------------------------------------------------------
def _extract_email(text):
    m = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    return m.group(0) if m else ''


def _extract_phone(text):
    m = re.search(
        r'(?:\+\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
        text
    )
    return m.group(0).strip() if m else ''


def _extract_name(text):
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    for line in lines[:8]:
        if re.search(r'[@/\\|:\d{4}]', line):
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w):
            return line
    return lines[0] if lines else 'Unknown'


def _skill_in_text(skill, text_lower):
    """Check if a skill phrase appears in text with word boundaries."""
    pattern = r'(?<![a-z0-9\-])' + re.escape(skill.lower()) + r'(?![a-z0-9\-])'
    return bool(re.search(pattern, text_lower))


def _extract_skills(text, extra_skills=None):
    text_lower = ' ' + text.lower() + ' '
    found = []
    all_skills = set(SKILLS)
    if extra_skills:
        all_skills.update(s.strip().lower() for s in extra_skills if s.strip())
    for skill in all_skills:
        if _skill_in_text(skill, text_lower):
            found.append(skill)
    return sorted(set(found))


def _extract_education(text):
    text_lower = text.lower()
    for pattern, level in EDUCATION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return level
    return 'high_school'


def _extract_experience(text):
    import datetime
    text_lower = text.lower()
    for pattern in EXPERIENCE_RE:
        matches = re.findall(pattern, text_lower)
        if matches:
            return float(max(int(m) for m in matches))
    total_months = 0
    current_year = datetime.date.today().year
    for m in DATE_RANGE_RE.finditer(text_lower):
        start_year = int(m.group(1))
        end_raw = m.group(2)
        end_year = current_year if end_raw in ('present', 'current', 'now') else int(end_raw)
        diff = max(0, end_year - start_year)
        total_months += diff * 12
    if total_months:
        return round(total_months / 12, 1)
    return 0.0


def _parse_resume(file_bytes, filename, mimetype='', extra_skills=None):
    raw = _extract_text(file_bytes, filename, mimetype)
    return {
        'raw_text':   raw,
        'name':       _extract_name(raw),
        'email':      _extract_email(raw),
        'phone':      _extract_phone(raw),
        'skills':     _extract_skills(raw, extra_skills=extra_skills),
        'education':  _extract_education(raw),
        'experience': _extract_experience(raw),
    }


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------
def _score(raw_text, detected_skills, exp_years, edu_level, job):
    req_skills = [s.strip().lower() for s in (job.required_skills or '').split(',') if s.strip()]
    raw_lower = ' ' + (raw_text or '').lower() + ' '

    def _req_matched(req):
        """Return 1.0 if the required skill is found in detected list or raw text."""
        if req in detected_skills:
            return 1.0
        if _skill_in_text(req, raw_lower):
            return 1.0
        return None  # needs fuzzy fallback

    # Skills (40%)
    if req_skills:
        try:
            from rapidfuzz import fuzz
            matched = 0.0
            for req in req_skills:
                exact = _req_matched(req)
                if exact is not None:
                    matched += exact
                else:
                    best = max((fuzz.ratio(req, ds) for ds in detected_skills), default=0)
                    matched += 0.9 if best >= 85 else (0.5 if best >= 70 else 0.0)
            skills_score = min(100.0, (matched / len(req_skills)) * 100)
        except ImportError:
            matched = sum(1.0 for r in req_skills if _req_matched(r) is not None)
            skills_score = min(100.0, (matched / len(req_skills)) * 100)
    else:
        skills_score = 60.0

    # Experience (25%)
    min_exp = max(job.min_experience or 0, 0)
    if min_exp == 0:
        exp_score = 100.0
    else:
        ratio = exp_years / min_exp
        exp_score = min(100.0, 100 + (ratio - 1) * 10) if ratio > 1 else min(100.0, ratio * 100)

    # Education (20%)
    edu_rank = {'high_school': 1, 'bachelor': 2, 'master': 3, 'phd': 4}
    req_edu  = 1 if (job.education_level or 'any') == 'any' else edu_rank.get(job.education_level, 2)
    cand_edu = edu_rank.get(edu_level or 'high_school', 1)
    edu_score = min(100.0, (cand_edu / max(req_edu, 1)) * 100)

    # Content TF-IDF (15%)
    jd = f"{job.name or ''} {job.required_skills or ''} {job.job_description or ''}"
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec = TfidfVectorizer(stop_words='english', max_features=5000, min_df=1)
        matrix = vec.fit_transform([jd, raw_text or ' '])
        content_score = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0]) * 100
    except Exception:
        content_score = 0.0

    overall = (skills_score * 0.40 + exp_score * 0.25 + edu_score * 0.20 + content_score * 0.15)
    return {
        'overall':    round(min(100.0, overall), 1),
        'skills':     round(skills_score, 1),
        'experience': round(min(100.0, exp_score), 1),
        'education':  round(edu_score, 1),
        'content':    round(content_score, 1),
    }


def _rerank_job(job):
    """Re-score all candidates for a job and update ranks."""
    scored = []
    for c in job.candidate_ids:
        skills = c.get_skills_list()
        s = _score(c.raw_text or '', skills, c.experience_years, c.education_level, job)
        c.write({
            'score_overall':    s['overall'],
            'score_skills':     s['skills'],
            'score_experience': s['experience'],
            'score_education':  s['education'],
            'score_content':    s['content'],
            'state': 'scored' if c.state not in ('shortlisted', 'rejected') else c.state,
        })
        scored.append((s['overall'], c.id))
    scored.sort(reverse=True)
    for rank, (_, cid) in enumerate(scored, 1):
        job.env['hr.resume.candidate'].browse(cid).write({'rank': rank})


def _candidate_dict(c, req_skills=None):
    req_skills = req_skills or []
    det = c.get_skills_list()
    raw_lower = ' ' + (c.raw_text or '').lower() + ' '
    state_labels = dict(c._fields['state'].selection)
    edu_labels   = dict(c._fields['education_level'].selection)

    def _skill_found(skill):
        return skill in det or _skill_in_text(skill, raw_lower)

    return {
        'id': c.id, 'name': c.name, 'email': c.email or '',
        'phone': c.phone or '', 'rank': c.rank,
        'score_overall':    c.score_overall,
        'score_skills':     c.score_skills,
        'score_experience': c.score_experience,
        'score_education':  c.score_education,
        'score_content':    c.score_content,
        'experience_years': c.experience_years,
        'education_level':  edu_labels.get(c.education_level or '', c.education_level or ''),
        'state':       c.state,
        'state_label': state_labels.get(c.state, c.state),
        'detected_skills': det[:15],
        'matched_skills':  [s for s in req_skills if _skill_found(s)],
        'missing_skills':  [s for s in req_skills if not _skill_found(s)],
        'file_name':   c.file_name or '',
    }


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------
class HrsdResumeController(http.Controller):

    # ── Page ──────────────────────────────────────────────────────────────────
    @http.route('/hrsd/resume', type='http', auth='user', website=False, methods=['GET'])
    def resume_page(self, job_id=None, **kw):
        if not request.env.user._is_internal():
            return request.redirect('/web/login')

        missing = _check_imports()
        jobs    = request.env['hr.resume.job'].sudo().search([], order='create_date desc')

        selected_job    = None
        candidates_data = []

        if job_id and job_id != 'new':
            selected_job = request.env['hr.resume.job'].sudo().browse(int(job_id))
            if not selected_job.exists():
                selected_job = None

        if not selected_job and jobs and job_id != 'new':
            selected_job = jobs[0]

        if selected_job:
            req_skills = [s.strip().lower() for s in (selected_job.required_skills or '').split(',') if s.strip()]
            for c in selected_job.candidate_ids.sorted('score_overall', reverse=True):
                candidates_data.append(_candidate_dict(c, req_skills))

        jobs_list = [{'id': j.id, 'name': j.name, 'count': j.candidate_count} for j in jobs]

        return request.render('hrsd.resume_page', {
            'missing_packages': missing,
            'jobs':         jobs_list,
            'selected_job': selected_job,
            'candidates':   candidates_data,
            'csrf_token':   request.csrf_token(),
            'brand':        get_hrsd_branding(request.env),
        })

    # ── Create / update job profile ───────────────────────────────────────────
    @http.route('/hrsd/resume/job/save', type='http', auth='user', methods=['POST'], csrf=False)
    def job_save(self, **kw):
        body = _json_body()
        name = (body.get('name') or '').strip()
        if not name:
            return _err('Job title is required.')

        vals = {
            'name':             name,
            'required_skills':  (body.get('required_skills')  or '').strip(),
            'preferred_skills': (body.get('preferred_skills') or '').strip(),
            'min_experience':   int(body.get('min_experience') or 0),
            'education_level':  body.get('education_level') or 'bachelor',
            'job_description':  (body.get('job_description') or '').strip(),
        }
        job_id = body.get('id')
        try:
            if job_id:
                job = request.env['hr.resume.job'].sudo().browse(int(job_id))
                if job.exists():
                    job.write(vals)
                    _rerank_job(job)
                else:
                    job = request.env['hr.resume.job'].sudo().create(vals)
            else:
                job = request.env['hr.resume.job'].sudo().create(vals)
        except Exception as e:
            _logger.exception("job_save error")
            return _err(str(e), 500)

        return _ok(id=job.id, name=job.name)

    # ── Upload resume (base64 JSON, one file at a time) ───────────────────────
    @http.route('/hrsd/resume/upload', type='http', auth='user', methods=['POST'], csrf=False)
    def resume_upload(self, **kw):
        missing = _check_imports()
        if missing:
            return _err(f"Missing packages: {', '.join(missing)}")

        body = _json_body()
        job_id    = int(body.get('job_id') or 0)
        file_name = body.get('file_name') or 'resume'
        file_b64  = body.get('file_data') or ''
        size_kb   = int(body.get('file_size_kb') or 0)

        if not job_id:
            return _err('No job profile selected.')
        if not file_b64:
            return _err('No file data received.')

        job = request.env['hr.resume.job'].sudo().browse(job_id)
        if not job.exists():
            return _err('Job profile not found.', 404)

        ext = os.path.splitext(file_name)[1].lower()
        if ext not in {'.pdf', '.docx', '.doc', '.txt'}:
            return _err(f'Unsupported file type: {ext}')

        try:
            file_bytes = base64.b64decode(file_b64)
        except Exception:
            return _err('Invalid base64 file data.')

        if len(file_bytes) > 10 * 1024 * 1024:
            return _err('File exceeds 10 MB limit.')

        mimetype = {
            '.pdf':  'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc':  'application/msword',
            '.txt':  'text/plain',
        }.get(ext, '')

        try:
            job_skill_terms = [s.strip() for s in (
                (job.required_skills or '') + ',' + (job.preferred_skills or '')
            ).split(',') if s.strip()]
            parsed = _parse_resume(file_bytes, file_name, mimetype, extra_skills=job_skill_terms)
            scores = _score(parsed['raw_text'], parsed['skills'], parsed['experience'], parsed['education'], job)
            cand = request.env['hr.resume.candidate'].sudo().create({
                'name':             parsed['name'],
                'email':            parsed['email'],
                'phone':            parsed['phone'],
                'job_id':           job_id,
                'file_data':        file_b64,
                'file_name':        file_name,
                'file_size_kb':     size_kb or len(file_bytes) // 1024,
                'raw_text':         parsed['raw_text'],
                'detected_skills':  json.dumps(parsed['skills']),
                'experience_years': parsed['experience'],
                'education_level':  parsed['education'],
                'score_overall':    scores['overall'],
                'score_skills':     scores['skills'],
                'score_experience': scores['experience'],
                'score_education':  scores['education'],
                'score_content':    scores['content'],
                'state':            'scored',
            })
        except Exception as e:
            _logger.exception("Failed to process/save candidate")
            return _err(str(e), 500)

        _rerank_job(job)
        req_skills = [s.strip().lower() for s in (job.required_skills or '').split(',') if s.strip()]
        return _ok(candidate=_candidate_dict(cand, req_skills))

    # ── Re-rank ───────────────────────────────────────────────────────────────
    @http.route('/hrsd/resume/rerank', type='http', auth='user', methods=['POST'], csrf=False)
    def resume_rerank(self, **kw):
        body   = _json_body()
        job_id = int(body.get('job_id') or 0)
        job    = request.env['hr.resume.job'].sudo().browse(job_id)
        if not job.exists():
            return _err('Job not found.', 404)
        _rerank_job(job)
        return _ok()

    # ── Update candidate status ───────────────────────────────────────────────
    @http.route('/hrsd/resume/candidate/status', type='http', auth='user', methods=['POST'], csrf=False)
    def candidate_status(self, **kw):
        body   = _json_body()
        cid    = int(body.get('id') or 0)
        status = body.get('status') or 'scored'
        if status not in {'scored', 'shortlisted', 'rejected'}:
            status = 'scored'
        rec = request.env['hr.resume.candidate'].sudo().browse(cid)
        if rec.exists():
            rec.write({'state': status})
        return _ok(state=status)

    # ── Delete candidate ──────────────────────────────────────────────────────
    @http.route('/hrsd/resume/candidate/delete', type='http', auth='user', methods=['POST'], csrf=False)
    def candidate_delete(self, **kw):
        body = _json_body()
        cid  = int(body.get('id') or 0)
        rec  = request.env['hr.resume.candidate'].sudo().browse(cid)
        if rec.exists():
            rec.unlink()
        return _ok()

    # ── Candidate detail (raw text) ───────────────────────────────────────────
    @http.route('/hrsd/resume/candidate/detail', type='http', auth='user', methods=['GET'])
    def candidate_detail(self, id=None, **kw):
        cid = int(id or 0)
        rec = request.env['hr.resume.candidate'].sudo().browse(cid)
        if not rec.exists():
            return _err('Candidate not found.', 404)
        return _ok(
            raw_text=rec.raw_text or '',
            name=rec.name,
            email=rec.email or '',
            phone=rec.phone or '',
        )

    # ── History (all candidates across all jobs) ──────────────────────────────
    @http.route('/hrsd/resume/history', type='http', auth='user', methods=['GET'])
    def resume_history(self, **kw):
        candidates = request.env['hr.resume.candidate'].sudo().search(
            [], order='create_date desc', limit=1000
        )
        edu_labels   = dict(request.env['hr.resume.candidate']._fields['education_level'].selection)
        state_labels = dict(request.env['hr.resume.candidate']._fields['state'].selection)
        data = []
        for c in candidates:
            data.append({
                'id':               c.id,
                'name':             c.name,
                'email':            c.email or '',
                'phone':            c.phone or '',
                'job_id':           c.job_id.id,
                'job_name':         c.job_id.name or '',
                'rank':             c.rank,
                'score_overall':    round(c.score_overall, 1),
                'score_skills':     round(c.score_skills, 1),
                'score_experience': round(c.score_experience, 1),
                'score_education':  round(c.score_education, 1),
                'score_content':    round(c.score_content, 1),
                'experience_years': c.experience_years,
                'education_level':  edu_labels.get(c.education_level or '', ''),
                'state':            c.state,
                'state_label':      state_labels.get(c.state, c.state),
                'file_name':        c.file_name or '',
                'uploaded_by':      c.uploaded_by.name or '',
                'create_date':      c.create_date.strftime('%d %b %Y, %H:%M') if c.create_date else '',
            })
        return request.make_response(
            json.dumps({'ok': True, 'candidates': data}),
            headers=[('Content-Type', 'application/json')]
        )

    # ── Export CSV ────────────────────────────────────────────────────────────
    @http.route('/hrsd/resume/export/<int:job_id>', type='http', auth='user', methods=['GET'])
    def resume_export(self, job_id, **kw):
        job = request.env['hr.resume.job'].sudo().browse(job_id)
        if not job.exists():
            return request.not_found()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Rank', 'Name', 'Email', 'Phone',
            'Overall Score', 'Skills Score', 'Experience Score', 'Education Score', 'Content Score',
            'Experience (yrs)', 'Education', 'Detected Skills', 'Status'
        ])
        for c in job.candidate_ids.sorted('score_overall', reverse=True):
            writer.writerow([
                c.rank, c.name, c.email or '', c.phone or '',
                f'{c.score_overall:.1f}%', f'{c.score_skills:.1f}%',
                f'{c.score_experience:.1f}%', f'{c.score_education:.1f}%', f'{c.score_content:.1f}%',
                c.experience_years, c.education_level or '',
                ', '.join(c.get_skills_list()), c.state,
            ])

        return request.make_response(output.getvalue(), headers=[
            ('Content-Type', 'text/csv; charset=utf-8'),
            ('Content-Disposition', f'attachment; filename="resume_ranking_{job_id}.csv"'),
        ])
