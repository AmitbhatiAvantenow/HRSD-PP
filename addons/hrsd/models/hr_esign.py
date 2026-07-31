import base64
import hashlib
import html
import io
import logging
import secrets
from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from ..controllers.resume_controller import _extract_text

_logger = logging.getLogger(__name__)

# Keyword heuristics for automatic document classification (no LLM available offline).
_CATEGORY_KEYWORDS = {
    'offer_letter': ['offer letter', 'we are pleased to offer', 'compensation', 'joining date'],
    'contract': ['employment contract', 'terms of employment', 'agreement', 'employer', 'employee shall'],
    'nda': ['non-disclosure', 'confidentiality agreement', 'nda', 'proprietary information'],
    'policy': ['policy', 'code of conduct', 'acknowledge', 'i have read and understood'],
    'appraisal': ['appraisal', 'performance review', 'rating', 'goals achieved'],
}


DOCUMENT_STATE = [
    ('draft', 'Draft'),
    ('sent', 'Sent'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('rejected', 'Rejected'),
    ('expired', 'Expired'),
    ('archived', 'Archived'),
]

SIGNER_STATUS = [
    ('pending', 'Pending'),
    ('viewed', 'Viewed'),
    ('signed', 'Signed'),
    ('rejected', 'Rejected'),
]

SIGNATURE_TYPE = [
    ('draw', 'Drawn'),
    ('type', 'Typed'),
    ('upload', 'Uploaded'),
]

CATEGORY = [
    ('offer_letter', 'Offer Letter'),
    ('contract', 'Employment Contract'),
    ('nda', 'NDA / Confidentiality'),
    ('policy', 'Policy Acknowledgment'),
    ('appraisal', 'Appraisal Form'),
    ('other', 'Other'),
]

WORKFLOW_TYPE = [
    ('parallel', 'Parallel (anyone, any order)'),
    ('sequential', 'Sequential (in order)'),
]

FIELD_TYPE = [
    ('signature', 'Signature'),
    ('initial', 'Initials'),
    ('name', 'Name'),
    ('email', 'Email'),
    ('phone', 'Phone'),
    ('company', 'Company'),
    ('text', 'Text'),
    ('multiline', 'Multiline'),
    ('checkbox', 'Checkbox'),
    ('radio', 'Radio'),
    ('selection', 'Selection'),
    ('date', 'Date'),
    ('strikethrough', 'Strikethrough'),
    ('stamp', 'Stamp'),
]

AUDIT_EVENTS = [
    ('created', 'Created'),
    ('sent', 'Sent'),
    ('viewed', 'Viewed'),
    ('signed', 'Signed'),
    ('rejected', 'Rejected'),
    ('reminded', 'Reminder Sent'),
    ('completed', 'Completed'),
    ('downloaded', 'Downloaded'),
    ('archived', 'Archived'),
]


# ---------------------------------------------------------------------------
# Signature-block PDF generation (source PDF + a page of per-signer boxes).
# Kept as plain functions (no `self`/env dependency beyond the passed-in
# document recordset) so the controller can reuse them for backward
# compatibility with documents created before the `final_signed_file_data`
# field existed.
# ---------------------------------------------------------------------------
def _draw_signature_box(c, x, y, w, h, signer):
    """Draw one signer's box: name/email header, their signature image (or a
    dashed 'awaiting signature' placeholder), and the signed date."""
    from reportlab.lib.utils import ImageReader

    signed = signer.status == 'signed'
    c.setStrokeColorRGB(0.31, 0.27, 0.9) if signed else c.setStrokeColorRGB(0.7, 0.7, 0.75)
    c.setDash([] if signed else [3, 3])
    c.setLineWidth(1.2)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.setDash([])

    c.setFont('Helvetica-Bold', 10.5)
    c.setFillColorRGB(0.12, 0.1, 0.18)
    c.drawString(x + 10, y + h - 18, (signer.name or '')[:34])
    c.setFont('Helvetica', 8.5)
    c.setFillColorRGB(0.42, 0.45, 0.5)
    c.drawString(x + 10, y + h - 30, (signer.email or '')[:40])

    if signed and signer.signature_data:
        try:
            sig_bytes = base64.b64decode(signer.signature_data)
            img = ImageReader(io.BytesIO(sig_bytes))
            c.drawImage(img, x + 10, y + 26, width=w - 20, height=h - 62, preserveAspectRatio=True, mask='auto', anchor='sw')
        except Exception:
            _logger.exception('Failed to draw signature image for signer %s', signer.id)
        c.setFont('Helvetica', 8)
        c.setFillColorRGB(0.42, 0.45, 0.5)
        signed_on = signer.signed_date.strftime('%d %b %Y, %H:%M') if signer.signed_date else '-'
        c.drawString(x + 10, y + 10, f'Signed: {signed_on}')
    else:
        c.setFont('Helvetica-Oblique', 9)
        c.setFillColorRGB(0.6, 0.6, 0.65)
        c.drawCentredString(x + w / 2, y + h / 2 - 4, 'Awaiting signature')

    c.setFillColorRGB(0, 0, 0)


def _build_signature_block_pdf(pdf_bytes, doc):
    """Append a signature-block page (a grid of per-signer boxes — name,
    signature image, signed date) to the document, one box per signer, laid
    out two per row and wrapping to further pages if there are many signers.
    Falls back to the original file untouched if PDF generation fails."""
    try:
        import PyPDF2
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import letter

        signers = doc.signer_ids.sorted('sequence')
        margin = 50
        page_w, page_h = letter
        cols = 2
        gap = 20
        box_w = (page_w - 2 * margin - gap) / cols
        box_h = 130
        header_h = 90

        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=letter)

        def draw_header(first_page):
            c.setFont('Helvetica-Bold', 16)
            c.setFillColorRGB(0.12, 0.1, 0.18)
            c.drawString(margin, page_h - 50, 'Signatures' if first_page else 'Signatures (continued)')
            if first_page:
                c.setFont('Helvetica', 10.5)
                c.setFillColorRGB(0.42, 0.45, 0.5)
                c.drawString(margin, page_h - 68, f'{doc.name}  ·  {doc.code}')
            c.setFillColorRGB(0, 0, 0)

        draw_header(True)
        cursor_y = page_h - header_h
        col = 0
        for signer in signers:
            if cursor_y - box_h < margin:
                c.showPage()
                draw_header(False)
                cursor_y = page_h - header_h
                col = 0
            x = margin + col * (box_w + gap)
            _draw_signature_box(c, x, cursor_y - box_h, box_w, box_h, signer)
            col += 1
            if col >= cols:
                col = 0
                cursor_y -= box_h + gap

        c.showPage()
        c.save()
        buf.seek(0)

        block_reader = PyPDF2.PdfFileReader(buf)
        original_reader = PyPDF2.PdfFileReader(io.BytesIO(pdf_bytes))
        writer = PyPDF2.PdfFileWriter()
        for i in range(original_reader.getNumPages()):
            writer.addPage(original_reader.getPage(i))
        for i in range(block_reader.getNumPages()):
            writer.addPage(block_reader.getPage(i))

        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        _logger.exception('Failed to build signature-block PDF; serving original file instead')
        return pdf_bytes


def _draw_field_box(c, x, y, w, h, field, signer):
    """Draw one placed field at its stored position on the actual page. Used
    once a document has real field placements (from the "Place Fields" wizard
    step) instead of the generic appended signature-block page.

    Signature/initial are drawn from the signer's captured signature image.
    Every other fillable type (name/email/phone/company/text/multiline/
    selection/date/checkbox/radio) is drawn from `field.value` — what the
    signer actually typed/checked/picked on the signing portal — so an empty
    box always means "not filled in yet", never a guess. Strikethrough/stamp
    are decorative and not tied to a value."""
    from reportlab.lib.utils import ImageReader

    label = dict(FIELD_TYPE).get(field.field_type, field.field_type)

    def placeholder(text):
        # A plain signature line — no box — with a small caption above it.
        gap = max(2, h * 0.12)
        c.setStrokeColorRGB(0.75, 0.75, 0.8)
        c.setLineWidth(0.8)
        c.line(x, y + gap, x + w, y + gap)
        c.setFont('Helvetica-Oblique', max(6, min(8, h * 0.35)))
        c.setFillColorRGB(0.65, 0.65, 0.7)
        c.drawCentredString(x + w / 2, y + gap + 3, text)
        c.setFillColorRGB(0, 0, 0)

    if field.field_type in ('signature', 'initial'):
        # Checked on signature_data alone (not also signer.status) — the two
        # are always written together by action_sign, so this is one fewer
        # way for the drawn box to fall out of sync with what was captured.
        if signer.signature_data:
            # Signature image sitting above a plain rule, like a paper
            # signature line — no box around it.
            gap = max(3, h * 0.12)
            try:
                sig_bytes = base64.b64decode(signer.signature_data)
                img = ImageReader(io.BytesIO(sig_bytes))
                c.drawImage(img, x, y + gap, width=w, height=max(h - gap, 1),
                            preserveAspectRatio=True, mask='auto', anchor='sw')
            except Exception:
                _logger.exception('Failed to draw signature image for field %s', field.id)
            c.setStrokeColorRGB(0.55, 0.55, 0.62)
            c.setLineWidth(0.8)
            c.line(x, y + gap * 0.4, x + w, y + gap * 0.4)
        else:
            # Name the signer right on the line — makes it visually obvious
            # this exact box is tied to one specific person.
            base_label = 'Initial here' if field.field_type == 'initial' else 'Sign here'
            placeholder(f'{base_label} — {signer.name}' if signer.name else base_label)
        return

    if field.field_type in ('checkbox', 'radio'):
        checked = field.value in ('1', 'true', 'True', 'on')
        c.setStrokeColorRGB(0.31, 0.27, 0.9) if checked else c.setStrokeColorRGB(0.7, 0.7, 0.75)
        c.setDash([] if checked else [3, 3])
        c.setLineWidth(1.2)
        c.rect(x, y, w, h, stroke=1, fill=0)
        c.setDash([])
        if checked:
            c.setLineWidth(1.4)
            c.line(x + w * 0.2, y + h * 0.5, x + w * 0.42, y + h * 0.22)
            c.line(x + w * 0.42, y + h * 0.22, x + w * 0.82, y + h * 0.82)
        return

    if field.field_type == 'strikethrough':
        c.setStrokeColorRGB(0.31, 0.27, 0.9)
        c.setLineWidth(1.4)
        c.line(x, y + h / 2, x + w, y + h / 2)
        return

    if field.field_type == 'stamp':
        applied = field.value in ('1', 'true', 'True', 'on')
        if applied:
            c.setStrokeColorRGB(0.31, 0.27, 0.9)
            c.setLineWidth(1.6)
            radius = min(w, h) / 2
            c.circle(x + w / 2, y + h / 2, radius, stroke=1, fill=0)
            c.setFont('Helvetica-Bold', max(6, min(8, radius * 0.4)))
            c.setFillColorRGB(0.31, 0.27, 0.9)
            c.drawCentredString(x + w / 2, y + h / 2 - 3, 'APPROVED')
            c.setFillColorRGB(0, 0, 0)
        else:
            placeholder(label)
        return

    # name / email / phone / company / text / multiline / selection / date —
    # all driven by whatever the signer actually entered on the portal.
    if field.value:
        font_size = max(6, min(9, h * 0.4))
        c.setFont('Helvetica', font_size)
        c.setFillColorRGB(0.12, 0.1, 0.18)
        if field.field_type == 'multiline':
            line_h = font_size + 2
            lines = str(field.value).splitlines() or ['']
            max_lines = max(1, int(h / line_h))
            text_y = y + h - line_h
            for line in lines[:max_lines]:
                c.drawString(x + 3, text_y, line[:80])
                text_y -= line_h
        else:
            c.drawString(x + 3, y + h / 2 - font_size / 3, str(field.value)[:70])
        c.setFillColorRGB(0, 0, 0)
    else:
        placeholder(label)


def _build_fields_overlay_pdf(pdf_bytes, doc):
    """Draw every placed field directly onto its page at its stored position
    — the real counterpart to the drag-and-drop "Place Fields" wizard step.
    Falls back to the generic appended signature-block page (or the original
    file) if anything goes wrong, so documents created without placed fields
    keep working exactly as before."""
    try:
        import PyPDF2
        from reportlab.pdfgen import canvas as rl_canvas

        original_reader = PyPDF2.PdfFileReader(io.BytesIO(pdf_bytes))
        num_pages = original_reader.getNumPages()

        fields_by_page = defaultdict(list)
        for field in doc.field_ids.sorted('sequence'):
            fields_by_page[field.page].append(field)

        writer = PyPDF2.PdfFileWriter()
        for i in range(num_pages):
            page = original_reader.getPage(i)
            page_fields = fields_by_page.get(i + 1)
            if page_fields:
                page_w = float(page.mediaBox.getWidth())
                page_h = float(page.mediaBox.getHeight())
                buf = io.BytesIO()
                c = rl_canvas.Canvas(buf, pagesize=(page_w, page_h))
                for field in page_fields:
                    x = field.pos_x / 100.0 * page_w
                    y = (1 - (field.pos_y + field.height) / 100.0) * page_h
                    w = field.width / 100.0 * page_w
                    h = field.height / 100.0 * page_h
                    _draw_field_box(c, x, y, w, h, field, field.signer_id)
                c.save()
                buf.seek(0)
                overlay_page = PyPDF2.PdfFileReader(buf).getPage(0)
                page.mergePage(overlay_page)
            writer.addPage(page)

        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        _logger.exception('Failed to build fields-overlay PDF; falling back to signature-block page')
        return _build_signature_block_pdf(pdf_bytes, doc)


class HrEsignDocument(models.Model):
    _name = 'hr.esign.document'
    _description = 'E-Sign Document'
    _order = 'create_date desc'
    _rec_name = 'name'

    code = fields.Char(string='Number', required=True, copy=False, readonly=True, default='New')
    name = fields.Char(string='Document Title', required=True)
    category = fields.Selection(CATEGORY, string='Category', default='other', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)

    file_data = fields.Binary(string='Document', required=True, attachment=True)
    file_name = fields.Char(string='File Name')
    file_hash = fields.Char(string='Content Hash', index=True, help='SHA-256 of the source file — used for duplicate detection.')
    extracted_text = fields.Text(string='Extracted Text', help='OCR/parsed text, used for search and metadata extraction.')

    final_signed_file_data = fields.Binary(
        string='Final Sign Doc', attachment=True,
        help='The source document with an appended signature-block page — regenerated every time a '
             'signer signs, so it always reflects the latest state (still-pending boxes shown as '
             '"Awaiting signature" until everyone has signed).')
    final_signed_file_name = fields.Char(string='Final Sign Doc Filename')

    template_id = fields.Many2one('hr.esign.template', string='Template')
    workflow_type = fields.Selection(WORKFLOW_TYPE, string='Workflow', default='parallel', required=True)
    priority = fields.Selection([('0', 'Normal'), ('1', 'High'), ('2', 'Urgent')], default='0', string='Priority')
    state = fields.Selection(DOCUMENT_STATE, string='Status', default='draft', required=True, tracking=True)

    created_by_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    sent_date = fields.Datetime(string='Sent On')
    due_date = fields.Date(string='Due Date')
    completed_date = fields.Datetime(string='Completed On')

    email_subject = fields.Char(string='Email Subject', help='Subject of the signing-request email. Defaults to "Signature requested: <document>" if left blank.')
    email_message = fields.Text(string='Message', help='Optional note included in the signing-request email, above the Review & Sign button.')
    cc_emails = fields.Char(string='CC', help='Comma-separated email addresses to copy on every signing-request email.')

    signer_ids = fields.One2many('hr.esign.signer', 'document_id', string='Signers')
    audit_ids = fields.One2many('hr.esign.audit.log', 'document_id', string='Audit Trail')
    field_ids = fields.One2many('hr.esign.field', 'document_id', string='Placed Fields')

    signer_count = fields.Integer(compute='_compute_signer_stats')
    signed_count = fields.Integer(compute='_compute_signer_stats')
    progress = fields.Float(compute='_compute_signer_stats', string='Progress (%)')

    @api.depends('signer_ids.status')
    def _compute_signer_stats(self):
        for rec in self:
            total = len(rec.signer_ids)
            signed = len(rec.signer_ids.filtered(lambda s: s.status == 'signed'))
            rec.signer_count = total
            rec.signed_count = signed
            rec.progress = round((signed / total) * 100, 1) if total else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('hr.esign.document') or 'New'
            if vals.get('file_data') and not vals.get('file_hash'):
                vals['file_hash'] = self._compute_file_hash(vals['file_data'])
        records = super().create(vals_list)
        for rec in records:
            rec._log_audit('created', 'Document created')
        return records

    @staticmethod
    def _compute_file_hash(file_data_b64):
        try:
            raw = file_data_b64 if isinstance(file_data_b64, bytes) else file_data_b64.encode()
            import base64 as _b64
            return hashlib.sha256(_b64.b64decode(raw)).hexdigest()
        except Exception:
            return False

    def _log_audit(self, event_type, description, partner_name=False):
        self.ensure_one()
        self.env['hr.esign.audit.log'].sudo().create({
            'document_id': self.id,
            'event_type': event_type,
            'description': description,
            'user_id': self.env.user.id,
            'actor_name': partner_name or self.env.user.name,
        })

    def action_send(self):
        for rec in self:
            if not rec.signer_ids:
                raise ValueError('Add at least one signer before sending.')
            rec.write({'state': 'sent', 'sent_date': fields.Datetime.now()})
            rec._log_audit('sent', f'Sent to {len(rec.signer_ids)} signer(s)')
            # Build the signature-block page up front (all boxes "Awaiting signature")
            # so the very first signer already sees it at the bottom of the preview.
            rec._regenerate_final_signed_pdf()
            rec.signer_ids._send_signing_email()
            rec.write({'state': 'in_progress'})

    def _regenerate_final_signed_pdf(self):
        """(Re)build the Final Sign Doc field: the source document plus a
        signature-block page reflecting every signer's current status. Called
        on send and after every signature so it's always up to date."""
        for rec in self:
            if not rec.file_data:
                continue
            try:
                pdf_bytes = base64.b64decode(rec.file_data)
                if rec.field_ids:
                    final_pdf = _build_fields_overlay_pdf(pdf_bytes, rec)
                else:
                    final_pdf = _build_signature_block_pdf(pdf_bytes, rec)
                rec.final_signed_file_data = base64.b64encode(final_pdf).decode()
                rec.final_signed_file_name = f"signed_{rec.file_name or 'document.pdf'}"
            except Exception:
                _logger.exception('Failed to regenerate Final Sign Doc for document %s', rec.id)

    def action_archive_document(self):
        self.write({'state': 'archived'})
        for rec in self:
            rec._log_audit('archived', 'Document archived')

    def action_download_signed(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/hrsd/sign/document/{self.id}/download',
            'target': 'self',
        }

    def _check_completion(self):
        for rec in self:
            if rec.signer_ids and all(s.status == 'signed' for s in rec.signer_ids):
                rec.write({'state': 'completed', 'completed_date': fields.Datetime.now()})
                rec._log_audit('completed', 'All signers have signed')

    @api.model
    def _cron_send_smart_reminders(self):
        """Nudge pending signers on documents idle for 3+ days, and flag documents
        past their due date as expired."""
        stale_cutoff = fields.Datetime.now() - relativedelta(days=3)
        in_progress = self.search([('state', '=', 'in_progress')])
        for doc in in_progress:
            stale_signers = doc.signer_ids.filtered(
                lambda s: s.status in ('pending', 'viewed') and doc.sent_date and doc.sent_date <= stale_cutoff
            )
            if stale_signers:
                stale_signers._send_signing_email()
                doc._log_audit('reminded', f'Reminder sent to {len(stale_signers)} pending signer(s)')

        overdue = self.search([
            ('state', 'in', ('sent', 'in_progress')),
            ('due_date', '!=', False),
            ('due_date', '<', fields.Date.today()),
        ])
        for doc in overdue:
            doc.write({'state': 'expired'})
            doc._log_audit('archived', 'Marked expired — past due date')

    def _event_trend_series(self, days=7):
        """Return a `series(event_type) -> [count, ...]` closure giving real daily
        counts for the last N days, bucketed from the audit log in one query."""
        today = fields.Date.today()
        start = fields.Datetime.to_string(datetime.combine(today - relativedelta(days=days - 1), datetime.min.time()))
        logs = self.env['hr.esign.audit.log'].sudo().search_read([('create_date', '>=', start)], ['event_type', 'create_date'])
        buckets = defaultdict(lambda: defaultdict(int))
        for log in logs:
            day = log['create_date'].date() if isinstance(log['create_date'], datetime) else log['create_date']
            buckets[log['event_type']][day] += 1
        day_list = [today - relativedelta(days=i) for i in range(days - 1, -1, -1)]

        def series(event_type):
            return [buckets[event_type].get(d, 0) for d in day_list]

        return series

    # -----------------------------------------------------------------------
    # Dashboard KPIs (called from the OWL landing page via the ORM service)
    # -----------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        Document = self.sudo()
        Signer = self.env['hr.esign.signer'].sudo()
        today_start = fields.Datetime.to_string(fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))

        pending_signatures = Signer.search_count([('status', 'in', ('pending', 'viewed'))])
        completed_today = Document.search_count([('state', '=', 'completed'), ('completed_date', '>=', today_start)])
        draft_documents = Document.search_count([('state', '=', 'draft')])
        waiting_approval = Document.search_count([('state', 'in', ('sent', 'in_progress'))])
        rejected = Document.search_count([('state', '=', 'rejected')])
        expiring = Document.search_count([
            ('state', 'in', ('sent', 'in_progress')),
            ('due_date', '!=', False),
            ('due_date', '<=', fields.Date.to_string(fields.Date.today() + relativedelta(days=3))),
        ])
        active_workflows = Document.search_count([('state', 'in', ('sent', 'in_progress'))])

        signed = Signer.search([('status', '=', 'signed'), ('viewed_date', '!=', False), ('signed_date', '!=', False)])
        durations = [(s.signed_date - s.viewed_date).total_seconds() for s in signed if s.signed_date and s.viewed_date]
        avg_seconds = round(sum(durations) / len(durations)) if durations else 0

        recent = Document.search([], limit=8, order='create_date desc')
        recent_activity = Document.env['hr.esign.audit.log'].sudo().search([], limit=10, order='create_date desc')

        # Real 7-day sparkline data per KPI card, bucketed from the audit log in a
        # single query (not fabricated — each series is an actual daily event count;
        # a few cards reuse the closest matching event type as an honest proxy since
        # there's no 1:1 daily event for e.g. "currently expiring").
        trend = self._event_trend_series()

        return {
            'kpis': {
                'pending_signatures': pending_signatures,
                'completed_today': completed_today,
                'avg_sign_seconds': avg_seconds,
                'draft_documents': draft_documents,
                'waiting_approval': waiting_approval,
                'rejected': rejected,
                'expiring_documents': expiring,
                'active_workflows': active_workflows,
                'total_documents': Document.search_count([]),
            },
            'trends': {
                'pending_signatures': trend('sent'),
                'completed_today': trend('completed'),
                'draft_documents': trend('created'),
                'waiting_approval': trend('sent'),
                'rejected': trend('rejected'),
                'expiring_documents': trend('reminded'),
                'active_workflows': trend('sent'),
                'total_documents': trend('created'),
                'avg_sign_seconds': trend('signed'),
            },
            'recent_documents': [{
                'id': d.id, 'name': d.name, 'code': d.code, 'state': d.state,
                'category': d.category, 'employee_name': d.partner_id.name, 'file_name': d.file_name or '',
                'progress': d.progress, 'signer_count': d.signer_count, 'signed_count': d.signed_count,
                'create_date': fields.Datetime.to_string(d.create_date),
            } for d in recent],
            'recent_activity': [{
                'id': a.id, 'event_type': a.event_type, 'description': a.description,
                'actor_name': a.actor_name, 'document_name': a.document_id.name,
                'document_id': a.document_id.id, 'create_date': fields.Datetime.to_string(a.create_date),
            } for a in recent_activity],
        }

    # -----------------------------------------------------------------------
    # AI document intelligence — OCR + classification + metadata + duplicates.
    # Uses the addon's existing (offline, no external API) text-extraction
    # pipeline. True semantic RAG would need an LLM API this environment
    # doesn't have configured; this is a solid keyword/heuristic stand-in.
    # -----------------------------------------------------------------------
    @api.model
    def ai_analyze_file(self, file_data, file_name):
        raw = base64.b64decode(file_data)
        text = _extract_text(raw, file_name or '', '') or ''
        file_hash = hashlib.sha256(raw).hexdigest()

        text_lower = text.lower()
        best_category, best_score = 'other', 0
        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_category, best_score = category, score

        duplicate = self.sudo().search([('file_hash', '=', file_hash)], limit=1)

        # First non-empty line as a suggested title.
        suggested_title = next((l.strip() for l in text.splitlines() if l.strip()), '') or (file_name or 'New Document')

        return {
            'extracted_text': text[:8000],
            'suggested_category': best_category,
            'suggested_title': suggested_title[:120],
            'is_duplicate': bool(duplicate),
            'duplicate_document': {'id': duplicate.id, 'name': duplicate.name, 'code': duplicate.code} if duplicate else False,
            'file_hash': file_hash,
        }

    @api.model
    def search_documents_smart(self, query):
        """Lightweight relevance search over title + extracted text (TF-IDF-free
        keyword scoring — fast, dependency-free, good enough for day-to-day use)."""
        query = (query or '').strip().lower()
        if not query:
            return []
        terms = [t for t in query.split() if t]
        docs = self.sudo().search([])
        scored = []
        for d in docs:
            haystack = f"{d.name} {d.code} {d.partner_id.name} {d.extracted_text or ''}".lower()
            score = sum(haystack.count(t) for t in terms)
            if score:
                scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{
            'id': d.id, 'name': d.name, 'code': d.code, 'state': d.state,
            'employee_name': d.partner_id.name,
        } for _, d in scored[:20]]


class HrEsignSigner(models.Model):
    _name = 'hr.esign.signer'
    _description = 'E-Sign Document Signer'
    _order = 'sequence, id'
    _rec_name = 'name'

    document_id = fields.Many2one('hr.esign.document', string='Document', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Order', default=10)

    partner_id = fields.Many2one('res.partner', string='Customer')
    name = fields.Char(string='Signer Name', required=True)
    email = fields.Char(string='Email', required=True)

    status = fields.Selection(SIGNER_STATUS, string='Status', default='pending', required=True)
    token = fields.Char(string='Access Token', copy=False, index=True, default=lambda self: secrets.token_urlsafe(32))
    sign_url = fields.Char(string='Link', compute='_compute_sign_url')

    viewed_date = fields.Datetime(string='Viewed On')
    signed_date = fields.Datetime(string='Signed On')
    signature_data = fields.Binary(string='Signature Image')
    signature_type = fields.Selection(SIGNATURE_TYPE, string='Signature Method')
    ip_address = fields.Char(string='IP Address')

    field_ids = fields.One2many('hr.esign.field', 'signer_id', string='Placed Fields')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            if rec.partner_id:
                rec.name = rec.partner_id.name
                rec.email = rec.partner_id.email

    @api.depends('token')
    def _compute_sign_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.sign_url = f"{base_url}/hrsd/sign/{rec.token}" if rec.token else False

    def _send_signing_email(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for signer in self:
            sign_url = f"{base_url}/hrsd/sign/{signer.token}"
            doc = signer.document_id
            custom_note = (
                f"<p style='white-space:pre-wrap;'>{html.escape(doc.email_message)}</p>" if doc.email_message else ""
            )
            body = (
                f"<p>Hello {signer.name},</p>"
                f"<p><strong>{doc.created_by_id.name}</strong> has requested your signature on "
                f"<strong>{doc.name}</strong>.</p>"
                f"{custom_note}"
                f"<p><a href='{sign_url}' style='background:#4f46e5;color:#fff;padding:10px 18px;"
                f"border-radius:8px;text-decoration:none;display:inline-block;'>Review &amp; Sign</a></p>"
                f"<p>Or copy this link: {sign_url}</p>"
            )
            self.env['mail.mail'].sudo().create({
                'subject': doc.email_subject or f'Signature requested: {doc.name}',
                'body_html': body,
                'email_to': signer.email,
                'email_cc': doc.cc_emails or False,
                'auto_delete': False,
            }).send()

    def action_mark_viewed(self):
        for rec in self:
            if rec.status == 'pending':
                rec.write({'status': 'viewed', 'viewed_date': fields.Datetime.now()})
                rec.document_id._log_audit('viewed', f'Viewed by {rec.name}', rec.name)

    def action_sign(self, signature_data, signature_type, ip_address=False):
        self.ensure_one()
        self.write({
            'status': 'signed',
            'signed_date': fields.Datetime.now(),
            'signature_data': signature_data,
            'signature_type': signature_type,
            'ip_address': ip_address,
        })
        self.document_id._log_audit('signed', f'Signed by {self.name}', self.name)
        self.document_id._regenerate_final_signed_pdf()
        self._send_confirmation_email()
        self.document_id._check_completion()

    def _send_confirmation_email(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        download_url = f"{base_url}/hrsd/sign/{self.token}/download"
        body = (
            f"<p>Hi {self.name},</p>"
            f"<p>You've successfully signed <strong>{self.document_id.name}</strong>.</p>"
            f"<p><a href='{download_url}' style='background:#4f46e5;color:#fff;padding:10px 18px;"
            f"border-radius:8px;text-decoration:none;display:inline-block;'>Download Signed Copy</a></p>"
        )
        self.env['mail.mail'].sudo().create({
            'subject': f'Signed: {self.document_id.name}',
            'body_html': body,
            'email_to': self.email,
            'auto_delete': False,
        }).send()

    def action_reject(self, reason=False):
        self.ensure_one()
        self.write({'status': 'rejected'})
        self.document_id.write({'state': 'rejected'})
        self.document_id._log_audit('rejected', f'Rejected by {self.name}' + (f': {reason}' if reason else ''), self.name)


class HrEsignField(models.Model):
    _name = 'hr.esign.field'
    _description = 'E-Sign Placed Field'
    _order = 'page, sequence, id'

    document_id = fields.Many2one('hr.esign.document', string='Document', required=True, ondelete='cascade', index=True)
    signer_id = fields.Many2one('hr.esign.signer', string='Signer', required=True, ondelete='cascade', index=True)
    field_type = fields.Selection(FIELD_TYPE, string='Field Type', required=True, default='signature')
    sequence = fields.Integer(string='Sequence', default=10)

    page = fields.Integer(string='Page', default=1, required=True, help='1-indexed PDF page this field is placed on.')
    pos_x = fields.Float(string='X (%)', required=True, help='Left offset as a percentage of the page width.')
    pos_y = fields.Float(string='Y (%)', required=True, help='Top offset as a percentage of the page height.')
    width = fields.Float(string='Width (%)', required=True)
    height = fields.Float(string='Height (%)', required=True)

    required = fields.Boolean(string='Required', default=True)
    placeholder = fields.Char(string='Label')
    value = fields.Char(string='Value', help='What the signer actually typed/checked/picked on the signing portal.')

    @api.constrains('document_id', 'signer_id')
    def _check_signer_belongs_to_document(self):
        for rec in self:
            if rec.signer_id.document_id != rec.document_id:
                raise ValidationError('A placed field must belong to a signer of the same document.')


class HrEsignTemplate(models.Model):
    _name = 'hr.esign.template'
    _description = 'E-Sign Document Template'
    _order = 'usage_count desc, name'

    name = fields.Char(string='Template Name', required=True)
    category = fields.Selection(CATEGORY, string='Category', default='other', required=True)
    file_data = fields.Binary(string='Template File', attachment=True)
    file_name = fields.Char(string='File Name')
    is_pinned = fields.Boolean(string='Pinned')
    usage_count = fields.Integer(string='Times Used', default=0)
    document_ids = fields.One2many('hr.esign.document', 'template_id', string='Documents')


class HrEsignAuditLog(models.Model):
    _name = 'hr.esign.audit.log'
    _description = 'E-Sign Audit Log'
    _order = 'create_date desc'
    _rec_name = 'description'

    document_id = fields.Many2one('hr.esign.document', string='Document', required=True, ondelete='cascade', index=True)
    event_type = fields.Selection(AUDIT_EVENTS, string='Event', required=True)
    description = fields.Char(string='Description', required=True)
    actor_name = fields.Char(string='Actor')
    user_id = fields.Many2one('res.users', string='Logged By')
