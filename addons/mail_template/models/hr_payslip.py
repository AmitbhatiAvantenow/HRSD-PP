# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import _, models
from odoo.exceptions import UserError

ATTACHMENT_CARD = Markup('''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2fb; border-radius:10px; margin-bottom:16px;">
  <tr><td style="padding:18px 20px;">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td style="width:52px; vertical-align:middle;">
        <table role="presentation" cellpadding="0" cellspacing="0" style="width:46px; height:46px; background:#ffffff; border:1px solid #d7e0f7; border-radius:50%;">
          <tr><td align="center" valign="middle" style="font-size:18px;">&#128196;</td></tr>
        </table>
      </td>
      <td style="padding-left:14px;">
        <div style="font-size:14px; font-weight:bold; color:#12328c;">__FILENAME__</div>
        <div style="font-size:12px; color:#6b7690; margin-top:2px;">Payslip Document</div>
        <div style="display:inline-block; margin-top:10px; padding:6px 14px; background:#1b4fd1; color:#ffffff; font-size:12px; border-radius:6px;">&#128206; Attached to this email</div>
      </td>
    </tr></table>
  </td></tr>
</table>
''')

NET_PAY_CARD = Markup('''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e3e8f3; border-radius:10px;">
  <tr><td style="padding:18px 20px;">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td style="width:50px; vertical-align:middle;">
        <table role="presentation" cellpadding="0" cellspacing="0" style="width:44px; height:44px; background:#e5f7ea; border-radius:50%;">
          <tr><td align="center" valign="middle" style="font-size:18px;">&#128176;</td></tr>
        </table>
      </td>
      <td style="padding-left:14px;">
        <div style="font-size:12px; color:#6b7690;">Net Pay</div>
        <div style="font-size:20px; font-weight:bold; color:#1f9254; margin-top:2px;">__NETPAY__</div>
      </td>
    </tr></table>
  </td></tr>
</table>
''')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_send_payslip_email(self):
        """Same flow as hr_payroll_community's action_send_payslip_email
        (build PDF, attach, send via the shared hr.payslip.mail.template
        subject/body/cc), but the mail body is now the modern branded
        layout from mail_template instead of a plain <br/>-joined string."""
        self.ensure_one()
        if not self.employee_id.work_email:
            raise UserError(_('%s has no work email set - cannot send the payslip.') % self.employee_id.name)

        template = self.env['hr.payslip.mail.template'].sudo().get_or_create()
        subject, body = self._render_payslip_mail(template)
        month = self.date_from.strftime('%B %Y') if self.date_from else ''
        net_pay = self.format_currency(self.get_salary_line_total('NET'))

        pdf_content, _fmt = self.env['ir.actions.report']._render_qweb_pdf(
            'hr_payroll_community.report_payslip', self.ids)
        filename = '%s_%s_Payslip.pdf' % (
            (self.employee_id.name or 'Employee').replace(' ', '_'),
            self.date_from.strftime('%B_%Y') if self.date_from else 'Payslip')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'raw': pdf_content,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        greeting = escape(body or '').replace('\n', Markup('<br/>'))
        if self.employee_id.name:
            # `new` must stay a Markup instance (not str()) so markupsafe
            # doesn't re-escape the tags we're intentionally injecting.
            greeting = greeting.replace(
                self.employee_id.name,
                Markup('<strong>%s</strong>') % self.employee_id.name, 1)

        body_content = (
            Markup('<p style="font-size:15px; margin:0 0 20px 0; line-height:1.7;">')
            + greeting + Markup('</p>')
            + ATTACHMENT_CARD.replace('__FILENAME__', filename)
            + NET_PAY_CARD.replace('__NETPAY__', net_pay)
        )

        Layout = self.env['mail.template.layout']
        full_body = Layout.render_modern_email(
            title=_('Payslip for %s') % month,
            body_content=body_content,
            preheader=_('Your payslip for %s is ready') % month,
            company=self.company_id,
            inline_logo=True,
        )
        cc_emails = [e.strip() for e in (template.cc or '').split(',') if e.strip()]
        msg = Layout.build_mime_message(
            subject=subject or _('Payslip'), html_body=full_body, to_email=self.employee_id.work_email,
            cc_emails=cc_emails, company=self.company_id,
            attachments=[{'filename': filename, 'data': pdf_content, 'maintype': 'application', 'subtype': 'pdf'}],
        )
        self.env['ir.mail_server'].sudo().send_email(msg)

        # Audit trail only: the actual delivery already happened above via a
        # hand-built MIME message (mail.mail's normal send path has no
        # support for inline Content-ID images, see Layout.build_mime_message).
        mail_vals = {
            'subject': subject or _('Payslip'),
            'body_html': full_body,
            'email_to': self.employee_id.work_email,
            'attachment_ids': [(6, 0, [attachment.id])],
            'auto_delete': True,
            'state': 'sent',
        }
        if cc_emails:
            mail_vals['email_cc'] = ', '.join(cc_emails)
        self.env['mail.mail'].sudo().create(mail_vals)
        return True
