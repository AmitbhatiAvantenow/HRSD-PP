import base64
import logging
import os
import re

from odoo import models, fields, api
from odoo.tools import html2plaintext

from ..controllers.resume_controller import (
    _extract_text, _extract_email, _extract_phone, _extract_name, _extract_experience, _parse_resume,
)
from ..controllers.recruitment_controller import _extract_requirement_fields

_logger = logging.getLogger(__name__)

PRIORITY_SELECTION = [
    ('1', '1 - Critical'),
    ('2', '2 - High'),
    ('3', '3 - Moderate'),
    ('4', '4 - Low'),
]

STATUS_SELECTION = [
    ('not_started', 'Hiring Not Started'),
    ('in_progress', 'Hiring In Progress'),
    ('to_deploy', 'To be deployed'),
    ('deployed', 'Deployed'),
    ('completed', 'Assignment Completed'),
    ('cancelled', 'Close-Cancelled'),
]

# Matches this module's requirement code sequence, e.g. "HRR0000009".
_REQUIREMENT_CODE_RE = re.compile(r'\bHRR\d{5,}\b', re.IGNORECASE)
_INBOUND_SUBJECT_TAG = 'RCHR'


class HrRecruitment(models.Model):
    _name = 'hr.recruitment'
    _inherit = ['mail.thread']
    _description = 'Recruitment Requirement'
    _order = 'create_date desc'
    _rec_name = 'job_title'

    code = fields.Char(string='Number', required=True, copy=False, readonly=True, default='New')
    requirement_for = fields.Char(string='Requirement For', default=lambda self: self.env.company.name)

    client_name = fields.Many2one('res.partner', string='Client Name', required=True)
    client_contact_person = fields.Char(string='Client Contact Person', required=True)
    coordinator_id = fields.Many2one('hr.employee', string='Coordinator', required=True)
    requestor_id = fields.Many2one('hr.employee', string='Requestor', required=True)
    assigned_to_id = fields.Many2one('hr.employee', string='Assigned To')

    skill = fields.Char(string='Skill', required=True)
    job_title = fields.Char(string='Job Title', required=True)
    priority = fields.Selection(PRIORITY_SELECTION, string='Priority', default='3', required=True)
    status = fields.Selection(STATUS_SELECTION, string='Status', default='not_started', required=True)
    job_description = fields.Text(string='Job Description', required=True)

    candidate_ids = fields.One2many('hr.recruitment.candidate', 'requirement_id', string='Interview Candidates')
    note_ids = fields.One2many('hr.recruitment.note', 'requirement_id', string='Work Notes')
    candidate_count = fields.Integer(compute='_compute_counts')
    note_count = fields.Integer(compute='_compute_counts')

    @api.depends('candidate_ids', 'note_ids')
    def _compute_counts(self):
        for rec in self:
            rec.candidate_count = len(rec.candidate_ids)
            rec.note_count = len(rec.note_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('hr.recruitment') or 'New'
        return super().create(vals_list)

    # -----------------------------------------------------------------------
    # Incoming email → auto-create requirement / candidate
    #
    # Any email whose subject starts with "RCHR" is treated as a recruitment
    # submission. The job/client details or the candidate's resume may be
    # written in the email body, attached as a document, or both — both are
    # scanned and auto-mapped onto the record's fields, same as the manual
    # "Upload Document" / "Upload Resume(s)" buttons on the Requirements page.
    # -----------------------------------------------------------------------
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        subject = (msg_dict.get('subject') or '').strip()
        if not subject.upper().startswith(_INBOUND_SUBJECT_TAG):
            return super().message_new(msg_dict, custom_values=custom_values)

        body_text = html2plaintext(msg_dict.get('body') or '')
        attachments = msg_dict.get('attachments') or []

        attach_texts = []
        resume_attachment = None
        for fname, fcontent in attachments:
            try:
                text = _extract_text(fcontent, fname, '') or ''
            except Exception:
                text = ''
            if text:
                attach_texts.append(text)
            try:
                parsed = _parse_resume(fcontent, fname, '')
            except Exception:
                parsed = {}
            if (parsed.get('email') or parsed.get('phone')) and not resume_attachment:
                resume_attachment = (fname, fcontent, parsed)

        combined_text = '\n'.join([body_text] + attach_texts)

        code_match = _REQUIREMENT_CODE_RE.search(subject + ' ' + combined_text)
        existing_requirement = self.browse()
        if code_match:
            existing_requirement = self.sudo().search([('code', '=', code_match.group(0).upper())], limit=1)

        candidate_info = resume_attachment
        if not candidate_info and existing_requirement:
            # No dedicated resume file — see if candidate details were written directly in the text.
            text_email = _extract_email(combined_text)
            text_phone = _extract_phone(combined_text)
            if text_email or text_phone:
                candidate_info = (False, False, {
                    'name': _extract_name(combined_text),
                    'email': text_email,
                    'phone': text_phone,
                    'experience': _extract_experience(combined_text),
                })

        if existing_requirement:
            if candidate_info:
                self._recruitment_create_candidate(existing_requirement, candidate_info)
            else:
                # References a known requirement but doesn't look like a candidate submission
                # (e.g. a status update) — log it as a work note instead of dropping it.
                self.env['hr.recruitment.note'].sudo().create({
                    'requirement_id': existing_requirement.id,
                    'author_id': self.env.user.id,
                    'body': (subject + '\n\n' + combined_text).strip()[:8000],
                })
            return existing_requirement.id

        requirement = self._recruitment_create_from_email(subject, body_text, combined_text, msg_dict)
        if resume_attachment:
            self._recruitment_create_candidate(requirement, resume_attachment)
        return requirement.id

    def _recruitment_create_candidate(self, requirement, candidate_info):
        fname, fcontent, parsed = candidate_info
        name = parsed.get('name') or ''
        if not name or name == 'Unknown':
            name = os.path.splitext(fname)[0] if fname else 'Unknown Candidate'

        vals = {
            'requirement_id': requirement.id,
            'name': name,
            'email': parsed.get('email') or '',
            'mobile': parsed.get('phone') or '',
            'experience_years': parsed.get('experience') or 0.0,
            'interview_status': 'to_interview',
        }
        if fcontent:
            vals['resume_data'] = base64.b64encode(fcontent).decode()
            vals['resume_filename'] = fname
        self.env['hr.recruitment.candidate'].sudo().create(vals)

    def _recruitment_create_from_email(self, subject, body_text, combined_text, msg_dict):
        req_fields = _extract_requirement_fields(combined_text, subject)
        sender_name = (msg_dict.get('email_from') or '').split('<')[0].strip(' "') or self.env.user.name

        fallback_title = subject[len(_INBOUND_SUBJECT_TAG):].strip(' :-–') or 'New Requirement'
        vals = {
            'client_name': self._recruitment_find_or_create_partner(req_fields.get('client_name') or 'Unspecified Client'),
            'client_contact_person': req_fields.get('client_contact_person') or sender_name or 'N/A',
            'coordinator_id': self._recruitment_find_or_create_employee(sender_name),
            'requestor_id': self._recruitment_find_or_create_employee(sender_name),
            'skill': req_fields.get('skill') or 'Not specified',
            'job_title': req_fields.get('job_title') or fallback_title,
            'job_description': req_fields.get('job_description') or body_text or subject,
        }
        return self.create(vals)

    def _recruitment_find_or_create_partner(self, name):
        name = (name or 'Unspecified Client').strip()
        Partner = self.env['res.partner'].sudo()
        partner = Partner.search([('name', '=ilike', name)], limit=1)
        if not partner:
            partner = Partner.create({'name': name, 'company_type': 'company'})
        return partner.id

    def _recruitment_find_or_create_employee(self, name):
        name = (name or self.env.user.name or 'Recruitment Bot').strip()
        Employee = self.env['hr.employee'].sudo()
        employee = Employee.search([('name', '=ilike', name)], limit=1)
        if not employee:
            employee = Employee.create({'name': name})
        return employee.id
