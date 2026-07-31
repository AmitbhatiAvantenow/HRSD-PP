import base64
import io
import json
import logging
import os
import re

from odoo import http
from odoo.http import request

from .controllers import get_hrsd_branding

_logger = logging.getLogger(__name__)

ALLOWED_MIMETYPES = {
    'application/pdf', 'image/jpeg', 'image/png',
    'image/tiff', 'image/bmp', 'image/webp',
}
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp'}
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------

def _ocr_imports():
    """Return (pytesseract, Image) or raise ImportError with install hint."""
    try:
        import pytesseract
        from PIL import Image
        return pytesseract, Image
    except ImportError as exc:
        raise ImportError(
            "Required packages missing. Install them with:\n"
            "  pip install pytesseract Pillow pdf2image\n"
            "Then install Tesseract OCR engine:\n"
            "  macOS:  brew install tesseract\n"
            "  Ubuntu: sudo apt install tesseract-ocr\n"
            "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        ) from exc


def _pdf_to_images(file_bytes):
    """Convert PDF bytes to list of PIL Images (requires pdf2image + poppler)."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise ImportError(
            "pdf2image not installed. Run: pip install pdf2image\n"
            "Also install Poppler:\n"
            "  macOS:  brew install poppler\n"
            "  Ubuntu: sudo apt install poppler-utils"
        )
    return convert_from_bytes(file_bytes, dpi=300)


def _run_ocr(file_bytes, mimetype, filename):
    """
    Run Tesseract OCR on the uploaded file.
    Returns dict: {text, confidence, page_count, error}
    """
    result = {'text': '', 'confidence': 0.0, 'page_count': 1, 'error': None}

    try:
        pytesseract, Image = _ocr_imports()
    except ImportError as exc:
        result['error'] = str(exc)
        return result

    is_pdf = mimetype == 'application/pdf' or (filename or '').lower().endswith('.pdf')

    try:
        if is_pdf:
            pages = _pdf_to_images(file_bytes)
            result['page_count'] = len(pages)
            images = pages
        else:
            img = Image.open(io.BytesIO(file_bytes))
            if img.mode not in ('RGB', 'L', 'RGBA'):
                img = img.convert('RGB')
            images = [img]

        texts, confidences = [], []
        for img in images:
            page_text = pytesseract.image_to_string(img, lang='eng', config='--psm 6')
            texts.append(page_text)
            try:
                data = pytesseract.image_to_data(img, lang='eng',
                                                  output_type=pytesseract.Output.DICT)
                valid = [c for c in data['conf']
                         if isinstance(c, (int, float)) and int(c) >= 0]
                if valid:
                    confidences.append(sum(valid) / len(valid))
            except Exception:
                pass

        separator = '\n\n─── Page Break ───\n\n'
        result['text'] = separator.join(texts) if len(texts) > 1 else (texts[0] if texts else '')
        result['confidence'] = round(
            sum(confidences) / len(confidences), 1
        ) if confidences else 0.0

    except ImportError as exc:
        result['error'] = str(exc)
    except Exception as exc:
        _logger.exception("OCR processing error")
        result['error'] = f"OCR failed: {exc}"

    return result


# ---------------------------------------------------------------------------
# Smart field extraction (regex-based NER for HR documents)
# ---------------------------------------------------------------------------

def _extract_smart_fields(text):
    """Detect and extract structured HR fields from raw OCR text."""
    fields = {}

    # Emails
    emails = list(set(re.findall(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text
    )))
    if emails:
        fields['emails'] = emails[:5]

    # Phone numbers (UAE + international)
    phones = list(set(re.findall(
        r'(?:\+971|00971|0)[\s\-]?(?:5[024568]|[234679])[\s\-]?\d{3}[\s\-]?\d{4}'
        r'|(?:\+\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
        text
    )))
    if phones:
        fields['phones'] = [p.strip() for p in phones[:5]]

    # Emirates ID: 784-YYYY-XXXXXXX-X
    eids = list(set(re.findall(r'784[\s\-]?\d{4}[\s\-]?\d{7}[\s\-]?\d', text)))
    if eids:
        fields['emirates_ids'] = eids

    # Passport number (1-2 letters + 6-9 digits)
    passports = list(set(re.findall(r'\b[A-Z]{1,2}\d{6,9}\b', text)))
    if passports:
        fields['passport_numbers'] = passports[:3]

    # Dates (DD/MM/YYYY, YYYY-MM-DD, "15 Jan 2024", etc.)
    dates = list(set(re.findall(
        r'\b(?:\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}'
        r'|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}'
        r'|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May'
        r'|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?'
        r'|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4})\b',
        text, re.IGNORECASE
    )))
    if dates:
        fields['dates'] = dates[:10]

    # Currency amounts
    amounts = list(set(re.findall(
        r'(?:AED|USD|INR|EUR|SAR|QAR|KWD|BHD|GBP)\s*[\d,]+(?:\.\d{1,2})?'
        r'|[\d,]+(?:\.\d{2})?\s*(?:AED|USD|INR|EUR|SAR|QAR)',
        text, re.IGNORECASE
    )))
    if amounts:
        fields['amounts'] = [a.strip() for a in amounts[:10]]

    # Employee name
    name_m = re.search(
        r'(?:Employee\s*Name|Full\s*Name|Name\s*of\s*Employee|Name)\s*[:\-]?\s*'
        r'([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+){1,4})',
        text
    )
    if name_m:
        fields['employee_name'] = name_m.group(1).strip()

    # Employee / Staff ID
    empid_m = re.search(
        r'(?:Employee\s*(?:ID|No\.?|Number)|Staff\s*(?:ID|No\.?))\s*[:\-]?\s*([A-Z0-9\-]{2,20})',
        text, re.IGNORECASE
    )
    if empid_m:
        fields['employee_id_code'] = empid_m.group(1).strip()

    # Designation / Job title
    desig_m = re.search(
        r'(?:Designation|Position|Job\s*Title|Role)\s*[:\-]?\s*([A-Za-z][A-Za-z &\/]{2,50})',
        text, re.IGNORECASE
    )
    if desig_m:
        fields['designation'] = desig_m.group(1).strip()

    # Department
    dept_m = re.search(
        r'Department\s*[:\-]?\s*([A-Za-z][A-Za-z &\/]{2,50})',
        text, re.IGNORECASE
    )
    if dept_m:
        fields['department'] = dept_m.group(1).strip()

    # Salary / basic pay
    salary_m = re.search(
        r'(?:Basic\s*(?:Salary|Pay)|Gross\s*Salary|Monthly\s*Salary)\s*[:\-]?\s*([\d,]+(?:\.\d{2})?)',
        text, re.IGNORECASE
    )
    if salary_m:
        fields['salary'] = salary_m.group(1).strip()

    return fields


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class HrsdOcrController(http.Controller):

    @http.route('/hrsd/ocr', type='http', auth='user', website=False, methods=['GET'])
    def ocr_page(self, **kw):
        if not request.env.user._is_internal():
            return request.redirect('/web/login')

        scans = request.env['hr.document.ocr'].sudo().search(
            [], limit=20, order='create_date desc'
        )
        employees = request.env['hr.employee'].sudo().search(
            [('active', '=', True)], limit=300, order='name'
        )

        doc_type_labels = dict(
            request.env['hr.document.ocr']._fields['document_type'].selection
        )

        history = [{
            'id': s.id,
            'name': s.name,
            'doc_type': doc_type_labels.get(s.document_type, s.document_type),
            'employee': s.employee_id.name if s.employee_id else '',
            'employee_id': s.employee_id.id if s.employee_id else 0,
            'employee_url': f'/odoo/employees/{s.employee_id.id}' if s.employee_id else '',
            'attachment_id': s.employee_attachment_id.id if s.employee_attachment_id else 0,
            'word_count': s.word_count,
            'page_count': s.page_count,
            'confidence': s.confidence,
            'state': s.state,
            'date': s.create_date.strftime('%d %b %Y %H:%M') if s.create_date else '',
            'scanned_by': s.scanned_by.name if s.scanned_by else '',
        } for s in scans]

        return request.render('hrsd.ocr_page', {
            'scan_history': history,
            'employees': employees,
            'csrf_token': request.csrf_token(),
            'brand': get_hrsd_branding(request.env),
        })

    @http.route('/hrsd/ocr/scan', type='http', auth='user', methods=['POST'], csrf=True)
    def ocr_scan(self, **post):
        """Receive uploaded file, run OCR, persist record, return JSON."""
        def _json(data, status=200):
            resp = request.make_response(
                json.dumps(data),
                headers=[('Content-Type', 'application/json')]
            )
            resp.status_code = status
            return resp

        upload = request.httprequest.files.get('file')
        if not upload:
            return _json({'success': False, 'error': 'No file received.'}, 400)

        file_bytes = upload.read()
        filename = upload.filename or 'document'
        mimetype = upload.content_type or 'application/octet-stream'
        ext = os.path.splitext(filename)[1].lower()

        if len(file_bytes) > MAX_FILE_BYTES:
            return _json({'success': False, 'error': 'File too large (max 20 MB).'}, 400)

        if mimetype not in ALLOWED_MIMETYPES and ext not in ALLOWED_EXTENSIONS:
            return _json({
                'success': False,
                'error': 'Unsupported file type. Please upload PDF, JPG, PNG, or TIFF.'
            }, 400)

        doc_type = post.get('doc_type', 'other')
        employee_id = int(post.get('employee_id') or 0)
        doc_name = (post.get('doc_name') or '').strip() or os.path.splitext(filename)[0]

        ocr = _run_ocr(file_bytes, mimetype, filename)
        smart = _extract_smart_fields(ocr['text']) if ocr['text'] and not ocr['error'] else {}

        file_b64 = base64.b64encode(file_bytes).decode()

        # If an employee is selected, save the file as an ir.attachment on them
        employee_attachment_id = False
        employee_name = ''
        employee_url = ''
        if employee_id:
            try:
                employee = request.env['hr.employee'].sudo().browse(employee_id)
                if employee.exists():
                    employee_name = employee.name
                    employee_url = f'/odoo/employees/{employee_id}'
                    att = request.env['ir.attachment'].sudo().create({
                        'name': f'{doc_name} ({dict(request.env["hr.document.ocr"]._fields["document_type"].selection).get(doc_type, doc_type)})',
                        'datas': file_b64,
                        'res_model': 'hr.employee',
                        'res_id': employee_id,
                        'mimetype': mimetype,
                        'description': f'Scanned via OCR Document Scanner',
                    })
                    employee_attachment_id = att.id
            except Exception:
                _logger.warning("Could not create employee attachment", exc_info=True)

        try:
            record = request.env['hr.document.ocr'].sudo().create({
                'name': doc_name,
                'document_type': doc_type,
                'employee_id': employee_id or False,
                'employee_attachment_id': employee_attachment_id or False,
                'file_data': file_b64,
                'file_name': filename,
                'file_size_kb': len(file_bytes) // 1024,
                'extracted_text': ocr['text'],
                'smart_fields': json.dumps(smart),
                'page_count': ocr['page_count'],
                'confidence': ocr['confidence'],
                'state': 'error' if ocr['error'] else 'done',
                'error_message': ocr['error'] or False,
            })
        except Exception as exc:
            _logger.exception("Failed to save OCR record")
            return _json({'success': False, 'error': f'Save failed: {exc}'}, 500)

        return _json({
            'success': True,
            'scan_id': record.id,
            'text': ocr['text'],
            'smart_fields': smart,
            'page_count': ocr['page_count'],
            'confidence': ocr['confidence'],
            'word_count': record.word_count,
            'error': ocr['error'],
            'employee_name': employee_name,
            'employee_url': employee_url,
            'attachment_id': employee_attachment_id,
        })

    @http.route('/hrsd/ocr/load/<int:scan_id>', type='http', auth='user', methods=['GET'])
    def ocr_load(self, scan_id, **kw):
        """Return saved scan data as JSON for re-display."""
        rec = request.env['hr.document.ocr'].sudo().browse(scan_id)
        if not rec.exists():
            return request.make_response(
                json.dumps({'success': False, 'error': 'Record not found'}),
                headers=[('Content-Type', 'application/json')], status=404
            )
        return request.make_response(
            json.dumps({
                'success': True,
                'scan_id': rec.id,
                'name': rec.name,
                'doc_type': rec.document_type,
                'text': rec.extracted_text or '',
                'smart_fields': rec.get_smart_fields_dict(),
                'page_count': rec.page_count,
                'confidence': rec.confidence,
                'word_count': rec.word_count,
                'state': rec.state,
                'error': rec.error_message or None,
                'employee_name': rec.employee_id.name if rec.employee_id else '',
                'employee_url': f'/odoo/employees/{rec.employee_id.id}' if rec.employee_id else '',
                'attachment_id': rec.employee_attachment_id.id if rec.employee_attachment_id else None,
            }),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/hrsd/ocr/delete/<int:scan_id>', type='http', auth='user', methods=['POST'], csrf=True)
    def ocr_delete(self, scan_id, **kw):
        rec = request.env['hr.document.ocr'].sudo().browse(scan_id)
        if rec.exists():
            rec.unlink()
        return request.make_response(
            json.dumps({'success': True}),
            headers=[('Content-Type', 'application/json')]
        )
