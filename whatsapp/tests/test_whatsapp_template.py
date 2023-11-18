# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo import exceptions
from odoo.addons.whatsapp.tests.common import WhatsAppCommon, MockIncomingWhatsApp
from odoo.tests import tagged, users


@tagged('wa_template')
class WhatsAppTemplate(WhatsAppCommon, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.basic_template = cls.env['whatsapp.template'].create({
            'body': 'Demo Template',
            'name': 'Demo Template',
            'template_name': 'demo_template',
            'status': 'approved',
            'wa_account_id': cls.whatsapp_account.id,
            'wa_template_uid': "461783963517285",
        })

    @users('user_wa_admin')
    def test_button_validation(self):
        template = self.env['whatsapp.template'].create({
            'body': 'Hello World',
            'name': 'Test-basic',
            'status': 'approved',
            'wa_account_id': self.whatsapp_account.id,
        })

        # Test that the WhatsApp message fails validation when a phone number button with an invalid number is added.
        with self.assertRaises(exceptions.UserError):
            self._add_button_to_template(
                template, button_type="phone_number",
                call_number="91 12345 12345", name="test call fail",
            )

        # Test that the WhatsApp message fails validation when a URL button with an invalid URL is added.
        with self.assertRaises(exceptions.ValidationError):
            self._add_button_to_template(
                template, button_type='url',
                name="test url fail", website_url="odoo.com",
            )

    @users('user_wa_admin')
    def test_template_button_dynamic_url(self):
        """ Test button with dynamic url """
        template = self.env['whatsapp.template'].create({
            'body': 'Dynamic url button template',
            'name': 'Test-dynamic',
            'status': 'approved',
            'wa_account_id': self.whatsapp_account.id,
            'button_ids': [
                Command.create({
                    'button_type': 'url', 'name': 'Button url',
                    'url_type': 'dynamic', 'website_url': 'https://www.example.com'
                }),
            ],
        })
        self.assertWATemplateVariables(
            template,
            [
                ('{{1}}', 'button', 'free_text', {'demo_value': 'https://www.example.com???'}),
            ]
        )

    @users('user_wa_admin')
    def test_template_preview(self):
        """ Test preview feature from template itself """
        template = self.env['whatsapp.template'].create({
            'body': 'feel free to contact {{1}}',
            'footer_text': 'Thanks you',
            'header_text': 'Header {{1}}',
            'header_type': 'text',
            'variable_ids': [
                (5, 0, 0),
                (0, 0, {
                    'name': "{{1}}",
                    'line_type': 'body',
                    'field_type': "free_text",
                    'demo_value': "Nishant",
                }),
                (0, 0, {
                    'name': "{{1}}",
                    'line_type': 'header',
                    'field_type': "free_text",
                    'demo_value': "Jigar",
                }),
            ],
            'wa_account_id': self.whatsapp_account.id,
        })
        template_preview = self.env['whatsapp.preview'].create({
            'wa_template_id': template.id
        })
        for expected_var in ['Nishant', 'Jigar']:
            self.assertIn(expected_var, template_preview.preview_whatsapp)

    @users('user_wa_admin')
    def test_template_content_dynamic(self):
        """ Test body with multiple variables """
        template = self.env['whatsapp.template'].create({
            'body': '''Hello I am {{1}},
Here my mobile number: {{2}},
You are coming from {{3}}.
Welcome to {{4}} office''',
            'name': 'Test-dynamic-complex',
            'status': 'approved',
            'wa_account_id': self.whatsapp_account.id,
        })
        self.assertWATemplateVariables(
            template,
            [('{{1}}', 'body', 'free_text', {'demo_value': 'Sample Value'}),
             ('{{2}}', 'body', 'free_text', {'demo_value': 'Sample Value'}),
             ('{{3}}', 'body', 'free_text', {'demo_value': 'Sample Value'}),
             ('{{4}}', 'body', 'free_text', {'demo_value': 'Sample Value'})]
        )

        template = self.env['whatsapp.template'].create({
            'body': '''Hello I am {{1}},
Here my mobile number: {{2}},
Welcome to {{3}} office''',
            'name': 'Test-dynamic-complex',
            'status': 'approved',
            'wa_account_id': self.whatsapp_account.id,
            'variable_ids': [
                Command.create({'name': "{{1}}", 'line_type': "body", 'field_type': "user_name", 'demo_value': "Nishant"}),
                Command.create({'name': "{{2}}", 'line_type': "body", 'field_type': "user_mobile", 'demo_value': "+91 12345 12345"}),
                Command.create({'name': "{{3}}", 'line_type': "body", 'field_type': "free_text", 'demo_value': "Odoo In"}),
            ],
        })
        self.assertWATemplateVariables(
            template,
            [('{{1}}', 'body', 'user_name', {'demo_value': 'Nishant'}),
             ('{{2}}', 'body', 'user_mobile', {'demo_value': '+91 12345 12345'}),
             ('{{3}}', 'body', 'free_text', {'demo_value': 'Odoo In'})]
        )

    @users('user_wa_admin')
    def test_template_header_type_attachment(self):
        """ Test header type attachment """
        for header_type, header_attachment in zip(
            ('image', 'video', 'document'),
            (self.image_attachment, self.video_attachment, self.document_attachment)
        ):
            with self.subTest(header_type=header_type):
                demo_header_attachment = header_attachment.copy()
                # TDE TOCHECK: remove sudo and check attachement rights
                template = self.env['whatsapp.template'].sudo().create({
                    'body': f'Header {header_type} template',
                    'header_attachment_ids': [(6, 0, demo_header_attachment.ids)],
                    'header_type': header_type,
                    'name': f'Header {header_type}',
                    'wa_account_id': self.whatsapp_account.id,
                })
                with self.mockWhatsappGateway():
                    template.button_submit_template()
                self.assertWATemplate(template)

    @users('user_wa_admin')
    def test_template_header_type_dynamic_text(self):
        """ Test dynamic text header """
        template = self.env['whatsapp.template'].create({
            'header_text': 'Header {{1}}',
            'header_type': 'text',
            'name': 'Header Text',
            'wa_account_id': self.whatsapp_account.id,
        })
        with self.mockWhatsappGateway():
            template.button_submit_template()
        self.assertWATemplate(
            template,
            template_variables=[
                ('{{1}}', 'header', 'free_text', {'demo_value': 'Sample Value'}),
            ],
        )

        template = self.env['whatsapp.template'].create({
            'header_text': 'Header {{1}}',
            'header_type': 'text',
            'name': 'Header Text 2',
            'variable_ids': [
                    (0, 0, {'name': '{{1}}', 'line_type': 'header', 'field_type': 'free_text', 'demo_value': 'Dynamic'}),
                ],
            'wa_account_id': self.whatsapp_account.id,
        })
        with self.mockWhatsappGateway():
            template.button_submit_template()
        self.assertWATemplate(
            template,
            template_variables=[
                ('{{1}}', 'header', 'free_text', {'demo_value': 'Dynamic'}),
            ],
        )

        for header_text in ['Hello {{1}} and {{2}}', 'hello {{2}}']:
            with self.assertRaises(exceptions.ValidationError):
                self.env['whatsapp.template'].create({
                    'header_type': 'text',
                    'header_text': header_text,
                    'name': 'Header Text 3',
                    'body': 'Body',
                    'wa_account_id': self.whatsapp_account.id,
                })

    @users('user_wa_admin')
    def test_template_header_type_location(self):
        """ Test location header type """
        template = self.env['whatsapp.template'].create({
            'header_type': 'location',
            'name': 'Header Location',
            'wa_account_id': self.whatsapp_account.id,
        })
        self.assertWATemplateVariables(
            template,
            [('name', 'location', 'free_text', {'demo_value': 'Sample Value'}),
             ('address', 'location', 'free_text', {'demo_value': 'Sample Value'}),
             ('latitude', 'location', 'free_text', {'demo_value': 'Sample Value'}),
             ('longitude', 'location', 'free_text', {'demo_value': 'Sample Value'}),
            ]
        )

        template = self.env['whatsapp.template'].create({
            'header_type': 'location',
            'name': 'Header Location 2',
            'variable_ids': [
                    (0, 0, {'name': 'name', 'line_type': 'location', 'demo_value': 'LocName'}),
                    (0, 0, {'name': 'address', 'line_type': 'location', 'demo_value': 'Gandhinagar, Gujarat'}),
                    (0, 0, {'name': 'latitude', 'line_type': 'location', 'demo_value': '23.192985'}),
                    (0, 0, {'name': 'longitude', 'line_type': 'location', 'demo_value': '72.6366633'}),
                ],
            'wa_account_id': self.whatsapp_account.id,
        })

        with self.mockWhatsappGateway():
            template.button_submit_template()
        self.assertWATemplate(
            template,
            template_variables=[
                ('name', 'location', 'free_text', {'demo_value': 'LocName'}),
                ('address', 'location', 'free_text', {'demo_value': 'Gandhinagar, Gujarat'}),
                ('latitude', 'location', 'free_text', {'demo_value': '23.192985'}),
                ('longitude', 'location', 'free_text', {'demo_value': '72.6366633'}),
            ],
        )


@tagged('wa_template')
class WhatsAppTemplateSync(WhatsAppCommon, MockIncomingWhatsApp):

    @users('user_wa_admin')
    def test_synchronize_without_existing_template_from_account(self):
        """ Test template sync with whatsapp where there is no existing template for that account in odoo """
        with self.mockWhatsappGateway():
            self.whatsapp_account.button_sync_whatsapp_account_templates()
        templates = self.env['whatsapp.template'].search([('wa_account_id', '=', self.whatsapp_account.id)])
        templates = templates.grouped('template_name')

        # Check template with simple text
        self.assertTrue(templates["test_simple_text"])
        self.assertWATemplate(
            templates["test_simple_text"],
            status='approved',
            fields_values={
                'name': 'Test Simple Text',
                'template_name': 'test_simple_text',
                'body': 'Hello, how are you? Thank you for reaching out to us.',
                'wa_template_uid': '972203162638803'
            }
        )

        # Check template with dynamic header and dynamic body
        self.assertTrue(templates["test_dynamic_header_with_dynamic_body"])
        self.assertWATemplate(
            templates["test_dynamic_header_with_dynamic_body"],
            status='approved',
            fields_values={
                'header_type': 'text',
                'header_text': 'Hello {{1}}',
                'body': 'Greetings of the day! I hope you are safe and doing well. \n '
                        'This is {{1}} from Odoo. My mobile number is {{2}}.\n'
                        'I will be happy to help you with any queries you may have.\n'
                        'Thank you',
                'wa_template_uid': '778510144283702',
            },
            template_variables=[
                ('{{1}}', 'header', 'free_text', {'demo_value': 'Nishant'}),
                ('{{1}}', 'body', 'free_text', {'demo_value': 'Jigar'}),
                ('{{2}}', 'body', 'free_text', {'demo_value': '+91 12345 12345'})
            ],
        )

        # Check template with location header
        self.assertTrue(templates["test_location_header"])
        self.assertWATemplate(
            templates["test_location_header"],
            status='approved',
            fields_values={
                'template_type': 'utility',
                'header_type': 'location',
                'wa_template_uid': '948089559317319'
            },
            template_variables=[
                ('name', 'location', 'free_text', {'demo_value': 'Sample Value'}),
                ('address', 'location', 'free_text', {'demo_value': 'Sample Value'}),
                ('latitude', 'location', 'free_text', {'demo_value': 'Sample Value'}),
                ('longitude', 'location', 'free_text', {'demo_value': 'Sample Value'}),
            ]
        )

        # Check template with dynamic header and dynamic body and dynamic button
        self.assertTrue(templates["test_dynamic_header_body_button"])
        self.assertWATemplate(
            templates["test_dynamic_header_body_button"],
            status='approved',
            fields_values={
                'header_type': 'text',
                'header_text': 'Hello {{1}}',
                'body': 'Greetings of the day! I hope you are safe and doing well. \n '
                        'This is {{1}} from Odoo. My mobile number is {{2}}.\n'
                        'I will be happy to help you with any queries you may have.\n'
                        'Thank you',
                'wa_template_uid': '605909939256361'
            },
            template_variables=[
                ('{{1}}', 'header', 'free_text', {'demo_value': 'Nishant'}),
                ('{{1}}', 'body', 'free_text', {'demo_value': 'Jigar'}),
                ('{{2}}', 'body', 'free_text', {'demo_value': '+91 12345 12345'}),
                ('{{1}}', 'button', 'free_text', {'demo_value': 'https://www.example.com/???'}),
            ]
        )

    def test_synchronize_with_existing_template_from_account(self):
        """ Test template sync with whatsapp where there is existing template for that account in odoo """
        with self.mockWhatsappGateway():
            self.whatsapp_account.button_sync_whatsapp_account_templates()
        templates = self.env['whatsapp.template'].search([('wa_account_id', '=', self.whatsapp_account.id)])
        templates = templates.grouped('template_name')
        # Now modify existing template and sync again
        templates["test_simple_text"].write(
            {
                'body': 'Hello, how are you? Thank you for reaching out to us. Modified',
                'template_type': 'utility'
            }
        )
        templates["test_location_header"].unlink()
        templates["test_dynamic_header_with_dynamic_body"].write({
            'header_text': 'Hello',
            'variable_ids': [
                Command.clear(),  # Remove existing variables
                Command.create({'name': "{{1}}", 'line_type': "body", 'field_type': "user_name", 'demo_value': "Jigar"}),
                Command.create({'name': "{{2}}", 'line_type': "body", 'field_type': "user_mobile", 'demo_value': "+91 12345 12345"}),
            ]})
        templates["test_dynamic_header_body_button"].write(
            {
                'status': 'draft',
                'body': 'Greetings of the day! I hope you are safe and doing well. \n ',
                'header_type': 'location',
                'button_ids': [],
            }
        )
        with self.mockWhatsappGateway():
            self.whatsapp_account.button_sync_whatsapp_account_templates()
        templates = self.env['whatsapp.template'].search([('wa_account_id', '=', self.whatsapp_account.id)])
        templates = templates.grouped('template_name')
        self.assertTrue(templates["test_location_header"])
        self.assertWATemplate(
            templates["test_dynamic_header_body_button"],
            status='approved',
            fields_values={
                'header_type': 'text',
                'header_text': 'Hello {{1}}',
                'body': 'Greetings of the day! I hope you are safe and doing well. \n '
                        'This is {{1}} from Odoo. My mobile number is {{2}}.\n'
                        'I will be happy to help you with any queries you may have.\n'
                        'Thank you',
                'wa_template_uid': '605909939256361'
            },
            template_variables=[
                ('{{1}}', 'header', 'free_text', {'demo_value': 'Nishant'}),
                ('{{1}}', 'body', 'free_text', {'demo_value': 'Jigar'}),
                ('{{2}}', 'body', 'free_text', {'demo_value': '+91 12345 12345'}),
                ('{{1}}', 'button', 'free_text', {'demo_value': 'https://www.example.com/???'}),
            ]
        )

        self.assertWATemplate(
            templates["test_dynamic_header_with_dynamic_body"],
            status='approved',
            fields_values={
                'header_text': 'Hello {{1}}'
            },
            template_variables=[
                ('{{1}}', 'header', 'free_text', {'demo_value': 'Nishant'}),
                ('{{1}}', 'body', 'user_name', {'demo_value': 'Jigar'}),
                ('{{2}}', 'body', 'user_mobile', {'demo_value': '+91 12345 12345'}),
            ]
        )

    def test_synchronize_with_existing_template_from_template_individual(self):
        """ Test template sync with whatsapp where there is existing template from template itself """
        with self.mockWhatsappGateway():
            self.whatsapp_account.button_sync_whatsapp_account_templates()
        templates = self.env['whatsapp.template'].search([('wa_account_id', '=', self.whatsapp_account.id)])
        templates = templates.grouped('template_name')
        # Now modify existing template and sync template one by one
        templates["test_simple_text"].write(
            {
                'body': 'Hello, how are you? Thank you for reaching out to us. Modified',
                'template_type': 'utility'
            }
        )
        with self.mockWhatsappGateway():
            templates["test_simple_text"].button_sync_template()
        self.assertWATemplate(
            templates["test_simple_text"],
            status='approved',
            fields_values={
                'template_type': 'marketing',
                'body': 'Hello, how are you? Thank you for reaching out to us.',
                'wa_template_uid': '972203162638803',

            }
        )

        templates["test_dynamic_header_body_button"].write(
            {
                'status': 'draft',
                'body': 'Greetings of the day! I hope you are safe and doing well. \n ',
                'header_type': 'location',
                'button_ids': [],
            }
        )
        with self.mockWhatsappGateway():
            templates["test_dynamic_header_body_button"].button_sync_template()
        self.assertWATemplate(
            templates["test_dynamic_header_body_button"],
            status='approved',
            fields_values={
                'header_type': 'text',
                'header_text': 'Hello {{1}}',
                'body': 'Greetings of the day! I hope you are safe and doing well. \n '
                        'This is {{1}} from Odoo. My mobile number is {{2}}.\n'
                        'I will be happy to help you with any queries you may have.\n'
                        'Thank you',
            },
            template_variables=[
                ('{{1}}', 'header', 'free_text', {'demo_value': 'Nishant'}),
                ('{{1}}', 'body', 'free_text', {'demo_value': 'Jigar'}),
                ('{{2}}', 'body', 'free_text', {'demo_value': '+91 12345 12345'}),
                ('{{1}}', 'button', 'free_text', {'demo_value': 'https://www.example.com/???'}),
            ]
        )

    def test_update_webhook(self):
        """ Test template update webhook for different fields """
        basic_template = self.env['whatsapp.template'].create({
            'body': 'Demo Template',
            'name': 'Demo Template',
            'status': 'approved',
            'template_name': 'demo_template',
            'wa_account_id': self.whatsapp_account.id,
            'wa_template_uid': "461783963517285",
        })

        update_scenarios = [
            ("message_template_status_update", {'status': 'pending'}, ('status', 'approved'), {
                "event": "APPROVED",
                "message_template_id": basic_template.wa_template_uid,
                "message_template_name": "basic_template",
            }),
            ("template_category_update", {}, ('template_type', 'utility'), {
                "message_template_id": basic_template.wa_template_uid,
                "message_template_name": "message_template_category_update",
                "previous_category": "MARKETING",
                "new_category": "UTILITY"
            }),
            ("message_template_quality_update", {'quality': 'green'}, ('quality', 'red'), {
                "message_template_id": basic_template.wa_template_uid,
                "message_template_name": "message_template_quality_update",
                "previous_quality_score": "GREEN",
                "new_quality_score": "RED"
            })
        ]

        for field, update_values, expected_values, data in update_scenarios:
            with self.subTest(field=field):
                self._update_template(basic_template, field, update_values, expected_values, data)

    def _update_template(self, template, field, update_values, expected_values, data):
        template.write(update_values)
        self._receive_template_update(field=field, account=self.whatsapp_account, data=data)
        self.assertEqual(template[expected_values[0]], expected_values[1])
