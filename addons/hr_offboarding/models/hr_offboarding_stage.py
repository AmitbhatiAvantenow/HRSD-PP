from odoo import fields, models


class HrOffboardingStage(models.Model):
    _name = 'hr.offboarding.stage'
    _description = 'Offboarding Exit Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        string='Folded in Pipeline',
        help='Collapse this column by default on the Exit Pipeline board.')
    color = fields.Integer(string='Color', default=0)
    is_final = fields.Boolean(
        string='Marks Offboarding as Completed',
        help='Records reaching this stage are considered fully offboarded.')
    has_clearance = fields.Boolean(
        string='Clearance Checkpoint',
        help='Show department clearance approvals when a journey reaches this stage.')
    has_assets = fields.Boolean(
        string='Asset Checkpoint',
        help='Show the asset return checklist when a journey reaches this stage.')
    has_documents = fields.Boolean(
        string='Document Checkpoint',
        help='Show the document checklist when a journey reaches this stage.')
    has_payroll = fields.Boolean(
        string='Payroll Checkpoint',
        help='Show the final settlement summary when a journey reaches this stage.')
    mail_template_id = fields.Many2one(
        'mail.template', string='Auto-Send Email',
        domain="[('model', '=', 'hr.offboarding.request')]",
        help='Automatically emailed to the employee when an exit request enters this stage.')
    description = fields.Char()
