import base64
import json
import logging

from markupsafe import Markup
from odoo import http
from odoo.http import request

from .controllers import require_hrsd_confidential_access

_logger = logging.getLogger(__name__)


def _json(data, status=200):
    resp = request.make_response(
        json.dumps(data),
        headers=[('Content-Type', 'application/json')],
    )
    resp.status_code = status
    return resp


def _get_signer(token):
    return request.env['hr.esign.signer'].sudo().search([('token', '=', token)], limit=1)


def _get_signed_pdf_bytes(doc):
    """Return the up-to-date signature-block PDF for a document: the stored
    `final_signed_file_data` if present, otherwise build it on the fly via
    the model (covers documents created before this field existed)."""
    if doc.final_signed_file_data:
        return base64.b64decode(doc.final_signed_file_data)
    doc._regenerate_final_signed_pdf()
    if doc.final_signed_file_data:
        return base64.b64decode(doc.final_signed_file_data)
    return base64.b64decode(doc.file_data)


class EsignPortalController(http.Controller):

    # -----------------------------------------------------------------------
    # Secure signing portal (public — recipients don't have Odoo accounts)
    # -----------------------------------------------------------------------
    @http.route('/hrsd/sign/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def esign_sign_page(self, token, **kw):
        signer = _get_signer(token)
        if not signer:
            return request.render('hrsd.esign_invalid_link_page', {})

        doc = signer.document_id
        if signer.status == 'pending':
            signer.action_mark_viewed()

        # Only offer this signer's own not-yet-signed fields as fillable —
        # once they've signed, the portal just shows the flattened preview.
        signer_fields = signer.field_ids.sorted('sequence') if signer.status != 'signed' else signer.env['hr.esign.field']
        # Served by our own token-gated /preview route below, not the generic
        # /web/content/<model>/... route — the public/portal user has no read
        # access to hr.esign.document, so that route 404s for every signer
        # (this signing link's token is the actual authorization here).
        pdf_url = f'/hrsd/sign/{token}/preview'

        return request.render('hrsd.esign_sign_page', {
            'signer': signer,
            'document': doc,
            'token': token,
            'pdf_url': pdf_url,
            'csrf_token': request.csrf_token(),
            'page_data_json': Markup(json.dumps({
                'token': token,
                'signer_status': signer.status,
                'signer_name': signer.name,
                'signer_email': signer.email,
                'pdf_url': pdf_url,
                'fields': [{
                    'id': f.id,
                    'field_type': f.field_type,
                    'page': f.page,
                    'pos_x': f.pos_x,
                    'pos_y': f.pos_y,
                    'width': f.width,
                    'height': f.height,
                    'required': f.required,
                    'value': f.value or '',
                } for f in signer_fields],
            })),
        })

    @http.route('/hrsd/sign/<string:token>/preview', type='http', auth='public', website=False, sitemap=False)
    def esign_sign_preview(self, token, **kw):
        signer = _get_signer(token)
        if not signer:
            return request.not_found()

        # Show the evolving signature-block document (with prior signers'
        # boxes already visible) once it exists, not just the raw upload.
        doc = signer.document_id
        if doc.final_signed_file_data:
            pdf_bytes = base64.b64decode(doc.final_signed_file_data)
            filename = doc.final_signed_file_name or 'document.pdf'
        elif doc.file_data:
            pdf_bytes = base64.b64decode(doc.file_data)
            filename = doc.file_name or 'document.pdf'
        else:
            return request.not_found()

        return request.make_response(pdf_bytes, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'inline; filename="{filename}"'),
        ])

    @http.route('/hrsd/sign/<string:token>/submit', type='http', auth='public', methods=['POST'], csrf=True)
    def esign_sign_submit(self, token, **post):
        signer = _get_signer(token)
        if not signer:
            return _json({'ok': False, 'error': 'Invalid or expired signing link.'}, 404)
        if signer.status == 'signed':
            return _json({'ok': False, 'error': 'This document has already been signed.'})

        signature_data = post.get('signature_data') or ''
        signature_type = post.get('signature_type') or 'draw'
        if not signature_data:
            return _json({'ok': False, 'error': 'A signature is required.'})

        b64 = signature_data.split(',')[-1]
        try:
            base64.b64decode(b64)
        except Exception:
            return _json({'ok': False, 'error': 'Invalid signature data.'})

        # Other placed fields (text/date/checkbox/…) this signer filled in
        # directly on the document preview, keyed by field id.
        field_values = {}
        raw_field_values = post.get('field_values')
        if raw_field_values:
            try:
                field_values = json.loads(raw_field_values)
            except Exception:
                field_values = {}

        signer_fields = signer.field_ids
        fillable_types = ('name', 'email', 'phone', 'company', 'text', 'multiline', 'selection', 'date', 'checkbox', 'radio', 'stamp')
        missing_required = signer_fields.filtered(
            lambda f: f.required and f.field_type in fillable_types
            and not str(field_values.get(str(f.id), '')).strip()
        )
        if missing_required:
            return _json({'ok': False, 'error': 'Please fill in all required fields before signing.'})

        for field in signer_fields:
            if str(field.id) in field_values:
                field.write({'value': str(field_values[str(field.id)])})

        signer.action_sign(b64, signature_type, request.httprequest.remote_addr)
        return _json({'ok': True})

    @http.route('/hrsd/sign/<string:token>/reject', type='http', auth='public', methods=['POST'], csrf=True)
    def esign_sign_reject(self, token, **post):
        signer = _get_signer(token)
        if not signer:
            return _json({'ok': False, 'error': 'Invalid or expired signing link.'}, 404)
        signer.action_reject(post.get('reason'))
        return _json({'ok': True})

    @http.route('/hrsd/sign/<string:token>/download', type='http', auth='public', website=False)
    def esign_download(self, token, **kw):
        signer = _get_signer(token)
        if not signer or signer.status != 'signed':
            return request.not_found()

        doc = signer.document_id
        doc._log_audit('downloaded', f'Signed copy downloaded by {signer.name}', signer.name)
        signed_pdf = _get_signed_pdf_bytes(doc)

        return request.make_response(signed_pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="signed_{doc.file_name or "document.pdf"}"'),
        ])

    # -----------------------------------------------------------------------
    # Backend download (HR side — any internal user, not tied to a token)
    # -----------------------------------------------------------------------
    @http.route('/hrsd/sign/document/<int:document_id>/download', type='http', auth='user', website=False)
    def esign_document_download(self, document_id, **kw):
        require_hrsd_confidential_access()
        doc = request.env['hr.esign.document'].sudo().browse(document_id)
        if not doc.exists() or not doc.file_data:
            return request.not_found()

        doc._log_audit('downloaded', f'Signed copy downloaded by {request.env.user.name}')
        signed_pdf = _get_signed_pdf_bytes(doc)

        return request.make_response(signed_pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="signed_{doc.file_name or "document.pdf"}"'),
        ])
