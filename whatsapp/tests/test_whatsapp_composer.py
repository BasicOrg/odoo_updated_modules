# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
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
        cls.customers = cls.env['res.partner'].create([
            {
                'country_id': cls.env.ref('base.in').id,
                'name': 'Customer-IN',
                'mobile': "+91 12345 67891"
            }, {
                'country_id': cls.env.ref('base.be').id,
                'name': 'Customer-BE',
                'mobile': "0456001122",
            }
        ])

        # templates (considered as approved)
        cls.template_basic, cls.template_dynamic_cplx = cls.env['whatsapp.template'].create([
            {
                'body': 'Hello World',
                'name': 'Test-basic',
                'status': 'approved',
                'wa_account_id': cls.whatsapp_account.id,
            }, {
                'body': '''Hello I am {{1}},
Here my mobile number: {{2}},
You are coming from {{3}}.
Welcome to {{4}} office''',
                'name': 'Test-dynamic-complex',
                'status': 'approved',
                'variable_ids': [
                    (5, 0, 0),
                    (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "user_name", 'demo_value': "Jigar"}),
                    (0, 0, {'name': "{{2}}", 'line_type': "body", 'field_type': "user_mobile", 'demo_value': "+91 12345 12345"}),
                    (0, 0, {'name': "{{3}}", 'line_type': "body", 'field_type': "field", 'demo_value': "sample country", 'field_name': 'country_id.name'}),
                    (0, 0, {'name': "{{4}}", 'line_type': "body", 'field_type': "free_text", 'demo_value': "Odoo In"}),
                ],
                'wa_account_id': cls.whatsapp_account.id,
            }
        ])

    @users('employee')
    def test_composer_check_user_number(self):
        """ When using 'user_mobile' in template variables, number should be
        set on sender. """
        template = self.template_dynamic_cplx.with_user(self.env.user)

        for mobile, should_crash in [
            (False, True),
            ('', True),
            ('zboing', False)
        ]:
            with self.subTest(mobile=mobile):
                self.env.user.mobile = mobile

                composer = self._instanciate_wa_composer_from_records(template, self.customers[0])
                if should_crash:
                    with self.assertRaises(exceptions.ValidationError), self.mockWhatsappGateway():
                        composer.action_send_whatsapp_template()
                else:
                    with self.mockWhatsappGateway():
                        composer.action_send_whatsapp_template()

    @users('user_wa_admin')
    def test_composer_preview(self):
        """ Test preview feature from composer """
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
        composer = self._instanciate_wa_composer_from_records(template, from_records=self.customers[0])
        for expected_var in ['Nishant', 'Jigar']:
            self.assertIn(expected_var, composer.preview_whatsapp)

    @users('employee')
    def test_composer_tpl_button(self):
        self._add_button_to_template(self.template_basic, 'test button')

        template = self.template_basic.with_env(self.env)
        composer = self._instanciate_wa_composer_from_records(template, from_records=self.customers[0])
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        self.assertWAMessage()

    @users('employee')
    def test_composer_tpl_button_phone_number(self):
        self._add_button_to_template(self.template_basic, name="test call", call_number='+91 (835) 902-5723', button_type='phone_number')

        template = self.template_basic.with_env(self.env)
        composer = self._instanciate_wa_composer_from_records(template, from_records=self.customers[0])
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        self.assertWAMessage()

    @users('employee')
    def test_composer_tpl_button_url(self):
        self._add_button_to_template(self.template_basic, name="test url", website_url='https://www.odoo.com/', button_type='url')

        template = self.template_basic.with_env(self.env)
        composer = self._instanciate_wa_composer_from_records(template, from_records=self.customers[0])
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        self.assertWAMessage()
