# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrCase(models.Model):
    _inherit = 'hr.case'

    @api.model
    def get_inquiry_type_options(self):
        """Return the list of selectable 'Type of Inquiry' options for the
        public dashboard, sourced from hr.case.category so the dropdown
        always reflects the real routing catalog (Division > Category).
        Only categories linked to an active division are returned.
        """
        services = self.env['hr.case.service'].search([('active', '=', True)])
        service_by_category = {service.category_id.id: service for service in services if service.category_id}
        service_by_division = {service.division_id.id: service for service in services if service.division_id}

        categories = self.env['hr.case.category'].browse(
            services.mapped('category_id').ids
        )
        categories |= self.env['hr.case.category'].search([
            ('active', '=', True),
            ('division_id.active', '=', True),
        ])

        options = []
        seen = set()
        for cat in categories:
            if cat.id in seen:
                continue
            seen.add(cat.id)
            service = service_by_category.get(cat.id) or service_by_division.get(cat.division_id.id)
            if not service:
                continue
            options.append({
                'id': cat.id,
                'name': cat.display_name or cat.name,
                'service_name': service.name,
                'service_id': service.id,
                'division_id': cat.division_id.id,
            })
        _logger = self.env['ir.logging'] if hasattr(self.env, 'ir_logging') else None
        if _logger:
            _logger.sudo().create({
                'name': 'hr_case_inquiry_dashboard.get_inquiry_type_options',
                'type': 'server',
                'dbname': self.env.cr.dbname,
                'level': 'INFO',
                'message': 'options=' + str(options),
                'path': 'hr_case_inquiry_dashboard.models.hr_case',
                'line': 1,
                'func': 'get_inquiry_type_options',
            })
        return options

    @api.model
    def create_from_inquiry_dashboard(self, values):
        """Create an hr.case from the standalone Employee Services Inquiry
        dashboard. `values` is the payload posted by the OWL widget.

        Expected keys: category_id (int, required), description (str, required),
        phone (str, optional), source (str, optional)
        """
        category_id = values.get('category_id')
        description = (values.get('description') or '').strip()

        if not category_id:
            raise UserError(_('Please select a Type of Inquiry before submitting.'))
        if not description:
            raise UserError(_('Please provide the details of your inquiry before submitting.'))

        category = self.env['hr.case.category'].browse(int(category_id))
        if not category.exists():
            raise UserError(_('The selected Type of Inquiry is no longer available. Please refresh and try again.'))

        division = category.division_id
        service = self.env['hr.case.service'].search([
            ('category_id', '=', category.id),
        ], limit=1)
        if not service:
            service = self.env['hr.case.service'].search([
                ('division_id', '=', division.id),
            ], limit=1)
        if not service:
            raise UserError(_(
                'No HR Service is configured for this Type of Inquiry yet. '
                'Please contact HR administration to configure routing for "%s".',
                category.display_name or category.name,
            ))

        employee = self.env.user.employee_id
        if not employee:
            raise UserError(_('No employee record is linked to your user account. '
                               'Please contact HR to set this up before submitting an inquiry.'))

        short_description = _('Employee Services Inquiry: %s', category.display_name or category.name)

        case_vals = {
            'employee_id': employee.id,
            'service_id': service.id,
            'division_id': division.id,
            'category_id': category.id,
            'short_description': short_description,
            'description': description,
            'source': values.get('source') or 'self_service',
        }

        case = self.create(case_vals)
        return {
            'id': case.id,
            'name': case.name,
            'state': case.state,
        }
