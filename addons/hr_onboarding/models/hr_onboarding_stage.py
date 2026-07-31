from odoo import fields, models


class HrOnboardingStage(models.Model):
    _name = 'hr.onboarding.stage'
    _description = 'Onboarding Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        string='Folded in Pipeline',
        help='Collapse this column by default on the New Hire Pipeline board.')
    color = fields.Integer(string='Color', default=0)
    is_final = fields.Boolean(
        string='Marks Onboarding as Completed',
        help='Records reaching this stage are considered fully onboarded.')
    has_documents = fields.Boolean(
        string='Document Checkpoint',
        help='Show the document checklist when a journey reaches this stage.')
    mail_template_id = fields.Many2one(
        'mail.template', string='Auto-Send Email',
        domain="[('model', '=', 'hr.onboarding')]",
        help='Automatically emailed to the new hire when an onboarding record enters this stage.')
    description = fields.Char()
