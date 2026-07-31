# -*- coding: utf-8 -*-
from odoo import fields, models


class HrCaseDivision(models.Model):
    """Top level grouping shown as 'Division' on the case form
    (e.g. Complaints, Requests, Disciplinary)."""
    _name = 'hr.case.division'
    _description = 'HR Case Division'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _name_company_uniq = models.Constraint(
        'unique(name, company_id)',
        'A division with this name already exists.',
    )


class HrCaseCategory(models.Model):
    """e.g. 'Salary / Payroll Complaint'."""
    _name = 'hr.case.category'
    _description = 'HR Case Category'
    _order = 'name'

    name = fields.Char(required=True)
    division_id = fields.Many2one('hr.case.division', string='Division', ondelete='cascade')
    active = fields.Boolean(default=True)


class HrCaseSubcategory(models.Model):
    """e.g. 'Salary' under 'Salary / Payroll Complaint'."""
    _name = 'hr.case.subcategory'
    _description = 'HR Case Subcategory'
    _order = 'name'

    name = fields.Char(required=True)
    category_id = fields.Many2one('hr.case.category', string='Category', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)


class HrCaseService(models.Model):
    """The HR Service catalog entry the employee picks first
    (e.g. 'Salary Complaint'), which can default a Division/Category."""
    _name = 'hr.case.service'
    _description = 'HR Service'
    _order = 'name'

    name = fields.Char(required=True)
    division_id = fields.Many2one('hr.case.division', string='Default Division')
    category_id = fields.Many2one('hr.case.category', string='Default Category')
    subcategory_id = fields.Many2one('hr.case.subcategory', string='Default Subcategory')
    description = fields.Text(string='Internal Notes')
    active = fields.Boolean(default=True)


class HrCaseTeam(models.Model):
    """Assignment Group: the team a case gets routed to, e.g. 'Finance - PAC Group'."""
    _name = 'hr.case.team'
    _description = 'HR Case Assignment Group'
    _order = 'name'

    name = fields.Char(required=True)
    manager_id = fields.Many2one('res.users', string='Team Leader')
    member_ids = fields.Many2many('res.users', 'hr_case_team_member_rel', 'team_id', 'user_id',
                                   string='Members')
    notification_email = fields.Char(string='Notification Email',
                                      help='Optional mailbox that also receives a copy of every '
                                           'notification raised for cases routed to this group.')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
