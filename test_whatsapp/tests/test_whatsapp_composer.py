# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.whatsapp.tests.common import WhatsAppCommon
from odoo.tests import tagged, users


@tagged('wa_composer')
class WhatsAppComposer(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # WRITE access on partner is required to be able to post a message on it
        cls.user_employee.write({'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)]})

        # test records for sending messages
        cls.test_base_records = cls.env['whatsapp.test.base'].create([
            {
                'country_id': cls.env.ref('base.in').id,
                'name': 'Recipient-IN',
                'phone': "+91 12345 67891"
            }, {
                'country_id': cls.env.ref('base.be').id,
                'name': 'Recipient-BE',
                'phone': "0456001122",
            }
        ])

        # templates (considered as approved)
        cls.template_basic, cls.template_dynamic, cls.template_dynamic_cplx = cls.env['whatsapp.template'].create([
            {
                'body': 'Hello World',
                'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
                'name': 'Test-basic',
                'status': 'approved',
                'wa_account_id': cls.whatsapp_account.id,
            }, {
                'body': 'Hello {{1}}',
                'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
                'name': 'Test-dynamic',
                'status': 'approved',
                'variable_ids': [
                    (5, 0, 0),
                    (0, 0, {'name': '{{1}}', 'line_type': 'body', 'field_type': 'field', 'demo_value': 'Customer', 'field_name': 'name'}),
                ],
                'wa_account_id': cls.whatsapp_account.id,
            }, {
                'body': '''Hello I am {{1}},
Here my mobile number: {{2}},
You are coming from {{3}}.
Welcome to {{4}} office''',
                'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
                'name': 'Test-dynamic-complex',
                'status': 'approved',
                'variable_ids': [
                    (5, 0, 0),
                    (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "user_name", 'demo_value': "Jigar"}),
                    (0, 0, {'name': "{{2}}", 'line_type': "body", 'field_type': "user_mobile", 'demo_value': "+91 12345 12345"}),
                    (0, 0, {'name': "{{3}}", 'line_type': "body", 'field_type': "field", 'demo_value': "sample country", 'field_name': 'country_id'}),
                    (0, 0, {'name': "{{4}}", 'line_type': "body", 'field_type': "free_text", 'demo_value': "Odoo In"}),
                ],
                'wa_account_id': cls.whatsapp_account.id,
            }
        ])

    @users('employee')
    def test_composer_tpl_base(self):
        """ Test basic sending, with template, without rendering """
        template = self.template_basic.with_user(self.env.user)
        test_record = self.test_base_records[0]
        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessageFromRecord(
            test_record,
            fields_values={
                'body': f'<p>{template.body}</p>',
            },
        )

    @users('employee')
    def test_composer_tpl_base_rendering(self):
        """ Test sending with template and rendering """
        free_text = 'Odoo In'
        template = self.template_dynamic_cplx.with_user(self.env.user)
        test_record = self.test_base_records[0]
        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessageFromRecord(
            test_record,
            fields_values={
                'body': f'<p>Hello I am {self.env.user.name},<br>Here my mobile number: {self.env.user.mobile},'
                        f'<br>You are coming from {test_record.country_id.name}.<br>Welcome to {free_text} office</p>',
            },
        )

    @users('employee')
    def test_composer_tpl_header_attachments(self):
        """ Send a template with a header attachment set through the composer."""
        doc_attach_clone = self.document_attachment.copy({'name': 'pdf_clone.pdf'})
        self.template_dynamic.write({
            'header_attachment_ids': [(6, 0, self.document_attachment.ids)],
            'header_type': 'document',
        })

        test_record = self.test_base_records[0].with_env(self.env)
        composer = self._instanciate_wa_composer_from_records(self.template_dynamic, test_record)
        composer.attachment_id = doc_attach_clone
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessageFromRecord(
            test_record,
            attachment_values={
                'name': 'pdf_clone.pdf',
            },
            fields_values={
                'body': f'<p>Hello {test_record.name}</p>',
            },
        )

    @users('employee')
    def test_composer_tpl_header_various(self):
        """ Test sending with rendering, including header """
        sample_text = 'Header Free Text'

        for header_type, template_upd_values, check_values in zip(
            ('text', 'text', 'image', 'video', 'document', 'location'),
            (
                {'header_text': 'Hello World'},
                {'header_text': 'Header {{1}}',
                 'variable_ids': [
                     (0, 0, {'name': '{{1}}', 'line_type': 'header', 'field_type': 'free_text', 'demo_value': sample_text})],
                 },
                {'header_attachment_ids': [(6, 0, self.image_attachment.ids)]},
                {'header_attachment_ids': [(6, 0, self.video_attachment.ids)]},
                {'header_attachment_ids': [(6, 0, self.document_attachment.ids)]},
                {'variable_ids': [
                    (0, 0, {'name': 'name', 'line_type': 'location', 'demo_value': 'LocName'}),
                    (0, 0, {'name': 'address', 'line_type': 'location', 'demo_value': 'Gandhinagar, Gujarat'}),
                    (0, 0, {'name': 'latitude', 'line_type': 'location', 'demo_value': '23.192985'}),
                    (0, 0, {'name': 'longitude', 'line_type': 'location', 'demo_value': '72.6366633'})],
                 },
            ), (
                {},
                {'body': f'<p>Header {sample_text}<br>Hello {self.test_base_records[0].name}</p>'},
                {},
                {},
                {},
                {},
            ),
        ):
            with self.subTest(header_type=header_type):
                self.template_dynamic.write({
                    'header_attachment_ids': [(5, 0, 0)],
                    'header_type': header_type,
                    **template_upd_values,
                })
                template = self.template_dynamic.with_user(self.env.user)
                composer = self._instanciate_wa_composer_from_records(template, self.test_base_records[0])
                with self.mockWhatsappGateway():
                    composer.action_send_whatsapp_template()

                fields_values = {
                    'body': f'<p>Hello {self.test_base_records[0].name}</p>',
                }
                fields_values.update(**(check_values or {}))
                self.assertWAMessageFromRecord(
                    self.test_base_records[0],
                    fields_values=fields_values,
                )
