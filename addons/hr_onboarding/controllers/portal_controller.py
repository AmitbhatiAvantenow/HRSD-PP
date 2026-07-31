import base64

from odoo import fields, http
from odoo.http import request


def _get_onboarding(token):
    return request.env['hr.onboarding'].sudo().search([('access_token', '=', token)], limit=1)


class HrOnboardingPortalController(http.Controller):

    @http.route('/onboarding/documents/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def onboarding_documents_page(self, token, submitted=None, **kw):
        onboarding = _get_onboarding(token)
        if not onboarding:
            return request.render('hr_onboarding.portal_invalid_link_page', {})

        return request.render('hr_onboarding.portal_documents_page', {
            'onboarding': onboarding,
            'token': token,
            'submitted': submitted,
            'csrf_token': request.csrf_token(),
        })

    @http.route('/onboarding/documents/<string:token>/submit', type='http', auth='public', methods=['POST'], csrf=True)
    def onboarding_documents_submit(self, token, **post):
        onboarding = _get_onboarding(token)
        if not onboarding:
            return request.render('hr_onboarding.portal_invalid_link_page', {})

        uploaded_count = 0
        for document in onboarding.document_ids:
            upload = request.httprequest.files.get(f'file_{document.id}')
            if upload and upload.filename:
                document.write({
                    'datas': base64.b64encode(upload.read()),
                    'datas_fname': upload.filename,
                    'status': 'uploaded',
                    'upload_date': fields.Datetime.now(),
                })
                uploaded_count += 1

        if post.get('declaration'):
            onboarding.write({
                'declaration_signed': True,
                'declaration_date': fields.Datetime.now(),
            })

        if uploaded_count:
            onboarding.message_post(
                body=f'Employee uploaded {uploaded_count} document(s) via the self-service portal.')

        return request.redirect(f'/onboarding/documents/{token}?submitted=1')
