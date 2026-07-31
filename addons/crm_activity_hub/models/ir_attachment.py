# -*- coding: utf-8 -*-
import base64
import logging
import os
import shutil
import subprocess
import tempfile

from odoo import models

_logger = logging.getLogger(__name__)

# Preview only makes sense for document-type Office formats — LibreOffice
# can convert all of these to PDF headlessly.
CONVERTIBLE_MIMETYPES = {
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.presentation',
    'application/rtf',
}

# Marks a generated PDF as a cached preview so we can find/invalidate it,
# without needing a dedicated field/model just for this.
PREVIEW_MARKER = 'crm_activity_hub_pdf_preview'

_CONVERT_TIMEOUT = 60


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def get_preview_pdf_attachment_id(self):
        """Return the id of a PDF rendition of this attachment, converting
        and caching it on first request. Returns False if this attachment's
        type can't be converted, or conversion isn't available/fails."""
        self.ensure_one()
        if self.mimetype not in CONVERTIBLE_MIMETYPES:
            return False

        cached = self.search([
            ('res_model', '=', 'ir.attachment'),
            ('res_id', '=', self.id),
            ('description', '=', PREVIEW_MARKER),
        ], limit=1)
        if cached:
            if cached.description == PREVIEW_MARKER and cached.create_date and self.write_date and cached.create_date >= self.write_date:
                return cached.id
            cached.sudo().unlink()

        pdf_data = self._crm_activity_hub_convert_to_pdf()
        if not pdf_data:
            return False

        pdf_attachment = self.env['ir.attachment'].sudo().create({
            'name': '%s.pdf' % (self.name or 'document'),
            'mimetype': 'application/pdf',
            'raw': pdf_data,
            'res_model': 'ir.attachment',
            'res_id': self.id,
            'description': PREVIEW_MARKER,
        })
        return pdf_attachment.id

    def _crm_activity_hub_convert_to_pdf(self):
        self.ensure_one()
        soffice = shutil.which('soffice') or shutil.which('libreoffice')
        if not soffice:
            _logger.warning("LibreOffice ('soffice') not found on PATH — cannot convert %s to PDF.", self.name)
            return False

        raw = self.raw
        if not raw:
            return False

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ext = os.path.splitext(self.name or '')[1] or '.bin'
                src_path = os.path.join(tmpdir, 'source%s' % ext)
                with open(src_path, 'wb') as f:
                    f.write(raw if isinstance(raw, bytes) else base64.b64decode(raw))

                subprocess.run(
                    [soffice, '--headless', '--norestore', '--convert-to', 'pdf', '--outdir', tmpdir, src_path],
                    check=True, timeout=_CONVERT_TIMEOUT,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )

                pdf_path = os.path.join(tmpdir, 'source.pdf')
                if not os.path.exists(pdf_path):
                    return False
                with open(pdf_path, 'rb') as f:
                    return f.read()
        except (subprocess.SubprocessError, OSError):
            _logger.exception("Preview conversion to PDF failed for attachment %s (%s)", self.id, self.name)
            return False
