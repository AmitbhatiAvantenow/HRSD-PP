# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class HrCaseInquiryDashboardController(http.Controller):

    @http.route('/employee-services/inquiry', type='http', auth='user')
    def inquiry_dashboard(self, **kwargs):
        """Standalone page (no backend menu) rendering the Employee Services
        Inquiry form. The page itself is a thin QWeb shell; all interactive
        behaviour is handled by the OWL widget mounted into it.
        """
        employee = request.env.user.employee_id
        values = {
            'employee_name': employee.name if employee else request.env.user.name,
        }
        return request.render('hr_case_inquiry_dashboard.inquiry_dashboard_page', values)

    @http.route('/employee-services/inquiry/options', type='jsonrpc', auth='user')
    def inquiry_dashboard_options(self, **kwargs):
        """Return current user/employee context + selectable inquiry types."""
        user = request.env.user
        employee = user.employee_id
        options = request.env['hr.case'].get_inquiry_type_options()
        return {
            'employee_name': employee.name if employee else user.name,
            'email': employee.work_email or user.email or '',
            'phone': employee.work_phone or '',
            'inquiry_types': options,
        }

    @http.route('/employee-services/inquiry/submit', type='jsonrpc', auth='user')
    def inquiry_dashboard_submit(self, **kwargs):
        """Create the hr.case from the submitted form payload and return
        the confirmation details for the success screen.
        """
        case = request.env['hr.case'].create_from_inquiry_dashboard(kwargs)
        return {
            'success': True,
            'case': case,
        }
