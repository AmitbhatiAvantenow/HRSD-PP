import html as html_lib
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrCaseProducer(models.Model):
    _name = 'hr.case.producer'
    _description = 'HR Service Form Template'
    _order = 'sequence, name'

    name = fields.Char(string='Form Name', required=True)
    sequence = fields.Integer(default=10)
    description = fields.Html(string='Instructions for Employees')
    service_id = fields.Many2one(
        'hr.case.service', string='HR Service', required=True,
        help='All submissions through this form will create cases under this service.'
    )
    image = fields.Image(string='Icon', max_width=256, max_height=256)
    active = fields.Boolean(default=True)
    question_ids = fields.One2many(
        'hr.case.producer.question', 'producer_id', string='Questions'
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    submission_count = fields.Integer(
        compute='_compute_submission_count', string='Submissions'
    )
    form_url = fields.Char(
        string='Form URL', compute='_compute_form_url', store=False
    )

    @api.constrains('service_id')
    def _check_service_routing(self):
        for rec in self:
            svc = rec.service_id
            if svc and (not svc.division_id or not svc.category_id):
                raise ValidationError(_(
                    "Service '%(service)s' must have Division and Category set "
                    "before it can be used in a form template. "
                    "Please update the service first.",
                    service=svc.name
                ))

    def _compute_submission_count(self):
        for rec in self:
            rec.submission_count = self.env['hr.case.submission'].search_count(
                [('producer_id', '=', rec.id)]
            )

    def _compute_form_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            # Backend dashboard URL — opens the OWL form within Odoo
            rec.form_url = (
                f'{base}/odoo/action-hr_case_management.action_hr_case_service_form'
                f'?producer_id={rec.id}'
            )

    def action_open_form_url(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.form_url,
            'target': 'new',
        }

    def action_open_submissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Submissions — %s') % self.name,
            'res_model': 'hr.case.submission',
            'view_mode': 'list,form',
            'domain': [('producer_id', '=', self.id)],
        }

    def action_start_submission(self):
        """Open the backend service-request OWL form for this template."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hr_case.service_form',
            'name': self.name,
            'context': {'producer_id': self.id},
            'target': 'current',
        }


class HrCaseProducerQuestion(models.Model):
    _name = 'hr.case.producer.question'
    _description = 'HR Service Form Question'
    _order = 'sequence, id'

    producer_id = fields.Many2one(
        'hr.case.producer', required=True, ondelete='cascade', index=True
    )
    sequence = fields.Integer(default=10)
    label = fields.Char(string='Question', required=True)
    field_type = fields.Selection([
        ('text', 'Short Text'),
        ('textarea', 'Long Text / Paragraph'),
        ('selection', 'Multiple Choice'),
        ('boolean', 'Yes / No'),
        ('date', 'Date'),
        ('employee', 'Employee'),
    ], string='Answer Type', required=True, default='text')
    required = fields.Boolean(string='Required', default=False)
    help_text = fields.Char(string='Helper Text')
    placeholder = fields.Char(string='Placeholder')
    selection_values = fields.Text(
        string='Choices',
        help='One choice per line. Used when Answer Type is "Multiple Choice".'
    )
    map_to_field = fields.Selection([
        ('short_description', 'Case Subject'),
        ('description', 'Case Description'),
        ('subject_person_id', 'Subject Employee'),
        ('due_date', 'Due Date'),
    ], string='Map to Case Field',
        help='Automatically copy this answer into a specific field on the created case.'
    )


class HrCaseSubmission(models.Model):
    _name = 'hr.case.submission'
    _description = 'HR Service Form Submission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', compute='_compute_name', store=True
    )
    producer_id = fields.Many2one(
        'hr.case.producer', string='Form', required=True,
        ondelete='restrict', readonly=True
    )
    producer_description = fields.Html(
        related='producer_id.description', string='Instructions', readonly=True
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Submitted By', required=True,
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        ),
        tracking=True,
    )
    short_description = fields.Char(
        string='Subject / Summary',
        help='Brief title for your request — becomes the HR case subject.'
    )
    answer_ids = fields.One2many(
        'hr.case.submission.answer', 'submission_id', string='Answers'
    )
    case_id = fields.Many2one('hr.case', string='Case Created', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
    ], string='Status', default='draft', readonly=True, tracking=True)
    date_submitted = fields.Datetime(string='Submitted On', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('producer_id', 'employee_id')
    def _compute_name(self):
        for rec in self:
            parts = [p for p in [rec.producer_id.name, rec.employee_id.name] if p]
            rec.name = ' — '.join(parts) if parts else _('New Request')

    def _normalize_subject_value(self, value):
        if value is None or isinstance(value, bool):
            return ''
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def action_submit(self):
        self.ensure_one()
        if self.state == 'submitted':
            raise UserError(_("This request has already been submitted."))

        for ans in self.answer_ids:
            if ans.required and not ans._has_value():
                raise ValidationError(
                    _("Please fill in the required field: %s") % ans.question_label
                )

        subject_text = self._normalize_subject_value(self.short_description)
        if not subject_text:
            raise ValidationError(_("Please enter a subject / summary before submitting this request."))

        producer = self.producer_id
        service = producer.service_id
        if not service.division_id or not service.category_id:
            raise UserError(_(
                "Form '%(form)s' is not fully configured. "
                "Please contact HR to set up the service routing (Division / Category).",
                form=producer.name
            ))

        sorted_answers = self.answer_ids.sorted(lambda a: a.question_id.sequence)
        rows_html = ''.join(
            '<tr>'
            '<td style="padding:5px 8px;font-weight:600;width:40%;'
            'border-bottom:1px solid #f0f0f0">'
            f'{html_lib.escape(ans.question_label or "")}'
            '</td>'
            '<td style="padding:5px 8px;border-bottom:1px solid #f0f0f0">'
            f'{html_lib.escape(ans._get_display_value() or "—")}'
            '</td>'
            '</tr>'
            for ans in sorted_answers
        )
        description_html = (
            '<table style="width:100%;border-collapse:collapse;font-size:14px">'
            '<thead><tr>'
            '<th style="text-align:left;padding:6px 8px;border-bottom:2px solid #dee2e6">'
            'Question</th>'
            '<th style="text-align:left;padding:6px 8px;border-bottom:2px solid #dee2e6">'
            'Answer</th>'
            '</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            '</table>'
        ) if rows_html else ''

        mapped = {}
        for ans in self.answer_ids:
            mf = ans.question_id.map_to_field
            if not mf:
                continue
            if mf == 'short_description':
                mapped_subject = self._normalize_subject_value(ans.value_char)
                if mapped_subject:
                    mapped['short_description'] = mapped_subject
            elif mf == 'description' and ans.value_text:
                mapped['description'] = ans.value_text
            elif mf == 'subject_person_id' and ans.value_employee_id:
                mapped['subject_person_id'] = ans.value_employee_id.id
            elif mf == 'due_date' and ans.value_date:
                mapped['due_date'] = ans.value_date

        subject = self._normalize_subject_value(mapped.get('short_description')) or subject_text
        if not subject:
            raise ValidationError(_("Please enter a subject / summary before submitting this request."))

        case_vals = {
            'employee_id': self.employee_id.id,
            'short_description': subject,
            'service_id': service.id,
            'division_id': service.division_id.id,
            'category_id': service.category_id.id,
            'source': 'self_service',
        }
        if service.subcategory_id:
            case_vals['subcategory_id'] = service.subcategory_id.id
        case_vals['description'] = mapped.get('description', description_html)
        for fld in ('subject_person_id', 'due_date'):
            if fld in mapped:
                case_vals[fld] = mapped[fld]

        case = self.env['hr.case'].create(case_vals)
        self.write({
            'state': 'submitted',
            'case_id': case.id,
            'date_submitted': fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Case Created'),
            'res_model': 'hr.case',
            'res_id': case.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_case(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.case',
            'res_id': self.case_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class HrCaseSubmissionAnswer(models.Model):
    _name = 'hr.case.submission.answer'
    _description = 'HR Service Form Answer'
    _order = 'question_id'

    submission_id = fields.Many2one(
        'hr.case.submission', required=True, ondelete='cascade', index=True
    )
    question_id = fields.Many2one(
        'hr.case.producer.question', required=True, ondelete='restrict', readonly=True
    )
    question_label = fields.Char(
        related='question_id.label', string='Question Text', store=True, readonly=True
    )
    field_type = fields.Selection(
        related='question_id.field_type', store=True, readonly=True
    )
    required = fields.Boolean(related='question_id.required', store=True, readonly=True)
    help_text = fields.Char(related='question_id.help_text', readonly=True)
    selection_values = fields.Text(related='question_id.selection_values', readonly=True)

    value_char = fields.Char(string='Answer (Text)')
    value_text = fields.Text(string='Answer (Long Text)')
    value_date = fields.Date(string='Answer (Date)')
    value_boolean = fields.Boolean(string='Answer (Yes/No)')
    value_employee_id = fields.Many2one('hr.employee', string='Answer (Employee)')
    value_selection = fields.Char(string='Answer (Selection)')

    answer_summary = fields.Char(
        string='Answer Summary',
        compute='_compute_answer_summary',
        store=False,
    )

    @api.depends(
        'field_type', 'value_char', 'value_text', 'value_date',
        'value_boolean', 'value_employee_id', 'value_selection',
    )
    def _compute_answer_summary(self):
        for rec in self:
            rec.answer_summary = rec._get_display_value()

    def _has_value(self):
        self.ensure_one()
        ft = self.field_type
        if ft == 'text':
            return bool(self.value_char)
        if ft == 'textarea':
            return bool(self.value_text)
        if ft == 'date':
            return bool(self.value_date)
        if ft == 'boolean':
            return True  # boolean is always answered (True or False)
        if ft == 'employee':
            return bool(self.value_employee_id)
        if ft == 'selection':
            return bool(self.value_selection)
        return False

    def _get_display_value(self):
        self.ensure_one()
        ft = self.field_type
        if ft == 'text':
            return self.value_char or ''
        if ft == 'textarea':
            return self.value_text or ''
        if ft == 'date':
            return fields.Date.to_string(self.value_date) if self.value_date else ''
        if ft == 'boolean':
            return _('Yes') if self.value_boolean else _('No')
        if ft == 'employee':
            return self.value_employee_id.name or ''
        if ft == 'selection':
            return self.value_selection or ''
        return ''
