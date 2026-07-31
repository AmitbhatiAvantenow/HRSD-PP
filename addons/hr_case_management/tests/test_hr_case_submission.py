from odoo.exceptions import ValidationError
from odoo.tests import common


class TestHrCaseSubmission(common.TransactionCase):
    def test_action_start_submission_allows_blank_subject(self):
        division = self.env['hr.case.division'].create({'name': 'Division'})
        category = self.env['hr.case.category'].create({'name': 'Category', 'division_id': division.id})
        service = self.env['hr.case.service'].create({
            'name': 'Service',
            'division_id': division.id,
            'category_id': category.id,
        })
        producer = self.env['hr.case.producer'].create({
            'name': 'Service Form',
            'service_id': service.id,
        })
        self.env['hr.case.producer.question'].create({
            'producer_id': producer.id,
            'label': 'What is the issue?',
            'field_type': 'text',
            'map_to_field': 'short_description',
        })

        employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        self.env.user.write({'employee_id': employee.id})

        action = producer.action_start_submission()
        submission = self.env['hr.case.submission'].browse(action['res_id'])

        self.assertTrue(submission.exists())
        self.assertFalse(submission.short_description)
        self.assertEqual(len(submission.answer_ids), 1)

    def test_action_submit_rejects_boolean_subject_without_crashing(self):
        division = self.env['hr.case.division'].create({'name': 'Division'})
        category = self.env['hr.case.category'].create({'name': 'Category', 'division_id': division.id})
        service = self.env['hr.case.service'].create({
            'name': 'Service',
            'division_id': division.id,
            'category_id': category.id,
        })
        producer = self.env['hr.case.producer'].create({
            'name': 'Service Form',
            'service_id': service.id,
        })
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        self.env.user.write({'employee_id': employee.id})

        submission = self.env['hr.case.submission'].create({
            'producer_id': producer.id,
            'employee_id': employee.id,
            'short_description': True,
        })

        with self.assertRaises(ValidationError):
            submission.action_submit()
