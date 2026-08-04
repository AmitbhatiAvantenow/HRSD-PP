import base64
import json
import logging

from odoo import api, fields, models

from . import face_engine

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _default_attendance_shift(self):
        return self.env.ref('flutterattendance.shift_general', raise_if_not_found=False)

    attendance_shift_id = fields.Many2one(
        'flutterattendance.shift',
        string='Attendance Shift',
        default=_default_attendance_shift,
    )
    attendance_device_ids = fields.One2many('flutterattendance.device', 'employee_id', string='Mobile Devices')

    # Face-recognition reference embedding, generated from image_1920 (see
    # write() below) by the same model that scores every check-in/out selfie
    # (models/face_engine.py) — the two must always come from that one model
    # for cosine similarity between them to mean anything.
    face_embedding = fields.Text(string='Face Embedding', copy=False)
    face_embedding_updated = fields.Datetime(string='Face Embedding Updated', copy=False)
    face_registered = fields.Boolean(string='Face Registered', compute='_compute_face_registered', store=True)

    @api.depends('face_embedding')
    def _compute_face_registered(self):
        for employee in self:
            employee.face_registered = bool(employee.face_embedding)

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for employee, vals in zip(employees, vals_list):
            if vals.get('image_1920'):
                employee._update_face_embedding()
        return employees

    def write(self, vals):
        result = super().write(vals)
        if 'image_1920' in vals:
            for employee in self:
                employee._update_face_embedding()
        return result

    def _update_face_embedding(self):
        self.ensure_one()
        if not self.image_1920:
            self.write({'face_embedding': False, 'face_embedding_updated': False})
            return
        try:
            image_bytes = base64.b64decode(self.image_1920)
            embedding = face_engine.embed_image_bytes(image_bytes)
        except Exception:
            _logger.exception("face_engine failed to process %s's profile photo", self.name)
            return
        if embedding is None:
            _logger.warning(
                "No face found in %s's profile photo — face_embedding left unchanged", self.name
            )
            return
        self.write({
            'face_embedding': json.dumps(embedding),
            'face_embedding_updated': fields.Datetime.now(),
        })
