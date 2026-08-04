from odoo import _, fields, models


class FlutterAttendanceFaceApproval(models.Model):
    _name = 'flutterattendance.face.approval'
    _description = 'Face Verification Approval Request'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    photo = fields.Binary(attachment=True, help="The selfie captured on the final failed attempt.")
    attendance_mode = fields.Selection(
        [('check_in', 'Check In'), ('check_out', 'Check Out')], required=True,
    )
    similarity_score = fields.Float(help="Best cosine similarity reached across the failed attempts.")
    attempt_count = fields.Integer()

    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    address = fields.Char()
    device_id = fields.Many2one('flutterattendance.device', string='Device')

    state = fields.Selection(
        [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending', required=True, index=True, tracking=True,
    )
    reviewed_by = fields.Many2one('res.users')
    reviewed_at = fields.Datetime()
    review_note = fields.Char()

    # The attendance record this request completed, once approved — lets
    # HR jump straight from the approval to the resulting check-in/out.
    attendance_id = fields.Many2one('flutterattendance.attendance', readonly=True)

    def action_approve(self):
        Attendance = self.env['flutterattendance.attendance'].sudo()
        for req in self:
            if req.state != 'pending':
                continue

            if req.attendance_mode == 'check_in':
                if Attendance._find_open_session(req.employee_id):
                    req.message_post(body=_(
                        "Could not approve: this employee already has an open check-in."))
                    continue
                record = Attendance.create({
                    'employee_id': req.employee_id.id,
                    'attendance_date': fields.Date.context_today(req.employee_id),
                    'check_in_time': fields.Datetime.now(),
                    'checkin_latitude': req.latitude,
                    'checkin_longitude': req.longitude,
                    'checkin_address': req.address,
                    'checkin_photo': req.photo,
                    'device_id': req.device_id.id if req.device_id else False,
                    'checkin_face_similarity': req.similarity_score,
                    'checkin_face_verified': False,
                })
            else:
                record = Attendance._find_open_session(req.employee_id)
                if not record:
                    req.message_post(body=_(
                        "Could not approve: no open check-in found to check out of."))
                    continue
                record.write({
                    'check_out_time': fields.Datetime.now(),
                    'checkout_latitude': req.latitude,
                    'checkout_longitude': req.longitude,
                    'checkout_address': req.address,
                    'checkout_photo': req.photo,
                    'checkout_created_at': fields.Datetime.now(),
                    'checkout_face_similarity': req.similarity_score,
                    'checkout_face_verified': False,
                })

            req.write({
                'state': 'approved',
                'reviewed_by': self.env.user.id,
                'reviewed_at': fields.Datetime.now(),
                'attendance_id': record.id,
            })

    def action_reject(self):
        self.write({
            'state': 'rejected',
            'reviewed_by': self.env.user.id,
            'reviewed_at': fields.Datetime.now(),
        })
