# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.whatsapp.tests.common import WhatsAppCommon, MockIncomingWhatsApp
from odoo.tests import tagged, users
from odoo.tools import mute_logger


class WhatsAppSecurityCase(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee2 = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='user.employee.2@test.mycompany.com',
            groups='base.group_user',
            login='company_1_test_employee_2',
        )


@tagged('wa_account', 'security')
class WhatsAppAccountSecurity(WhatsAppSecurityCase):

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_account_access(self):
        """ Test MC-enabled access on whastapp account model """
        # main company access only
        self.assertTrue(self.whatsapp_account.with_user(self.user_admin).name)
        self.assertTrue(self.whatsapp_account.with_user(self.user_employee).name)
        with self.assertRaises(exceptions.AccessError):
            self.assertTrue(self.whatsapp_account.with_user(self.user_employee_c2).name)

        # open to second company
        account_admin = self.whatsapp_account.with_user(self.user_admin)
        account_admin.write({
            'allowed_company_ids': [(4, self.company_2.id)],
        })
        self.assertTrue(self.whatsapp_account.with_user(self.user_employee_c2).name)

    @users('admin')
    def test_account_defaults(self):
        """ Ensure default configuration of account, notably MC / notification
        values. """
        account = self.env['whatsapp.account'].create({
            'account_uid': 'azerty',
            'app_secret': 'azerty',
            'app_uid': 'contact',
            'name': 'Test Account',
            'phone_uid': '987987',
            'token': 'TestToken',
        })
        self.assertEqual(account.allowed_company_ids, self.env.user.company_id)
        self.assertEqual(account.notify_user_ids, self.env.user)


@tagged('wa_account', 'security', 'post_install', '-at_install')
class WhatsAppControllerSecurity(MockIncomingWhatsApp, WhatsAppSecurityCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.whatsapp_account.app_secret = '1234567890abcdef'

    @mute_logger('odoo.addons.whatsapp.controller.main')
    def test_signature_verification(self):
        # valid signature for
        # >>> {"entry": [{"id": "abcdef123456"}]}
        signature = '0a354a1c094d43355c4b478408ba4344564de72fc8ff9699a64ea9095ecb5415'
        response = self._make_webhook_request(
            self.whatsapp_account,
            headers={'X-Hub-Signature-256': f'sha256={signature}'})
        # the endpoint return nothing when everything is fine
        self.assertFalse(response.get('result'))

        # wrong calls
        for signature in [
            False,  # no signature
            'sha256=',  # empty
            signature,  # wrong format
            f'sha256=a{signature[1:]}',  # wrong
        ]:
            with self.subTest(signature=signature):
                headers = {'X-Hub-Signature-256': signature} if signature else None
                response = self._make_webhook_request(self.whatsapp_account, headers=headers)
                self.assertIn("403 Forbidden", response.get('error', {}).get('data', {}).get('message'))


@tagged('wa_message', 'security')
class WhatsAppDiscussSecurity(WhatsAppSecurityCase):

    @users('admin')
    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_member_creation(self):
        channel_channel, channel_wa = self.env['discuss.channel'].create([
            {
                'channel_type': 'channel',
                'name': 'Test',
                'whatsapp_number': '+32456001122',
            }, {
                'channel_type': 'whatsapp',
                'name': 'Test',
                'whatsapp_number': '+32456001122',
            }
        ])
        with self.assertRaises(exceptions.ValidationError):
            channel_channel.with_user(self.user_employee).with_context(
                default_rtc_session_ids=[(0, 0, {'is_screen_sharing_on': True})]
            ).whatsapp_channel_join_and_pin()

        with self.assertRaises(exceptions.AccessError):
            channel_wa.with_user(self.user_employee).with_context(
                default_rtc_session_ids=[(0, 0, {'is_screen_sharing_on': True})]
            ).whatsapp_channel_join_and_pin()


@tagged('wa_message', 'security')
class WhatsAppMessageSecurity(WhatsAppSecurityCase):

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_message_signup_token(self):
        """Assert the template values sent to the whatsapp API are not fetched
        as sudo/SUPERUSER, even when going through the cron/queue. """

        # As group_system, create a template to send signup links to new users
        # through whatsapp.It sounds relatively reasonable as valid use case
        # that an admin wants to send user invitation links through a WA message
        env = self.env(user=self.user_admin)
        whatsapp_template_signup = env['whatsapp.template'].create({
            'name': 'foo',
            'body': 'Signup link: {{1}}',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'status': 'approved',
            'variable_ids': [
                (0, 0, {
                    'name': '{{1}}',
                    'line_type': 'body',
                    'field_type': 'field',
                    'demo_value': 'Customer',
                    'field_name': 'signup_url'
                }),
            ],
            'wa_account_id': self.whatsapp_account.id,
        })

        # Ask for the reset password of the admin
        # This mimics what the `/web/reset_password` URL does, which is publicly available, you just have to know
        # the login of your targeted user ('admin').
        # https://github.com/odoo/odoo/blob/554e6b0898727b6c08a9702e19ea8f2d67632c38/addons/auth_signup/controllers/main.py#L91
        # We could also directly call `/web/reset_password` within this unit test, but this would require:
        # - to convert the test to an httpcase
        # - to get and send the CSRF token.
        # Given the extra overhead, and the fact this is not what we are testing here,
        # just call directly `res.users.reset_password` as sudo, as the `/web/reset_password` route does
        env['res.users'].sudo().reset_password(self.user_admin.login)

        # As whatsapp_admin, take the opportunity of the above whatsapp template
        # to try to use it against the admin, and retrieve his signup token, allowing
        # the whatsapp_admin to change the password of the system admin
        env = self.env(user=self.user_wa_admin)
        # Ensure the whatsapp admin can indeed not read the signup url directly
        with self.assertRaisesRegex(exceptions.AccessError, "You are not allowed to modify 'User'"):
            env.ref('base.user_admin').partner_id.signup_url

        # Now, try to access the signup url of the admin user through a message sent to whatsapp.
        mail_message = self.user_admin.partner_id.message_post(body='foo')
        whatsapp_message = env['whatsapp.message'].create({
            'mail_message_id': mail_message.id,
            'mobile_number': '+32478000000',
            'wa_account_id': whatsapp_template_signup.wa_account_id.id,
            'wa_template_id': whatsapp_template_signup.id,
        })

        # Flush before calling the cron, to write in database pending writes
        # (e.g. `mobile_number_formatted`, which is computed based on `mobile_number`)
        env.flush_all()

        # Use the test_mode/TestCursor
        # To handle the `cr.commit()` in the `send_cron` method:
        # it shouldn't actually commit the transaction, as we are in a test, but simulate it,
        # which is the goal of the test_mode/TestCursor
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)
        cron_cr = self.registry.cursor()
        self.addCleanup(cron_cr.close)

        # Process the queue to send the whatsapp message through the cron/queue,
        # as the cron queue would do.
        with self.mockWhatsappGateway():
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                cron_cr,
                self.env.ref('whatsapp.ir_cron_send_whatsapp_queue').read(load=None)[0]
            )

        # Invalidate the cache of the whatsapp message, to force fetching the new values,
        # as the cron wrote on the message using another cursor
        whatsapp_message.invalidate_recordset()
        self.assertEqual(whatsapp_message.failure_reason, "Not able to get the value of field 'signup_url'")


@tagged('wa_template', 'security')
class WhatsAppTemplateSecurity(WhatsAppSecurityCase):

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_tpl_create(self):
        """ Creation is for WA admins only """
        Template_admin = self.env['whatsapp.template'].with_user(self.user_wa_admin)
        template = Template_admin.create({'body': 'Hello', 'name': 'Test'})
        self.assertEqual(template.model, 'res.partner')

        Template_emp = self.env['whatsapp.template'].with_user(self.user_employee)
        with self.assertRaises(exceptions.AccessError):
            template = Template_emp.create({'body': 'Hello', 'name': 'Test'})

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_tpl_read_allowed_users(self):
        """ Test 'allowed_users' that restricts access to the template """
        Template_admin = self.env['whatsapp.template'].with_user(self.user_wa_admin)
        template = Template_admin.create({'body': 'Hello', 'name': 'Test'})

        self.assertTrue(template.with_user(self.user_employee).name)
        self.assertTrue(template.with_user(self.user_employee2).name)

        # update, limit allowed users
        template.write({'allowed_user_ids': [(4, self.user_wa_admin.id), (4, self.user_employee.id)]})
        self.assertTrue(template.with_user(self.user_employee).name)
        with self.assertRaises(exceptions.AccessError):
            self.assertTrue(template.with_user(self.user_employee2).name)

    def test_tpl_safe_field_access(self):
        # Create a WhatsApp admin user with specific groups and permissions related to WhatsApp functionality.
        template = self.env['whatsapp.template'].create({
            'body': "hello, I am from '{{1}}'.",
            'name': 'Test Template',
            'status': 'approved',
            'model_id': self.env.ref('base.model_res_users').id,
            'phone_field': 'phone_sanitized',
        })

        # Verify that a System User can use any field in template.
        template.with_user(self.user_admin).variable_ids = [
            (5, 0, 0),
            (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "field", 'demo_value': "pwned", 'field_name': 'password'}),
        ]

        # Verify that a WhatsApp Admin can't set unsafe fields in template variable
        with self.assertRaises(exceptions.ValidationError):
            template.with_user(self.user_wa_admin).variable_ids = [
                (5, 0, 0),
                (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "field", 'demo_value': "pwned", 'field_name': 'password'}),
            ]

        with self.assertRaises(exceptions.ValidationError):
            template.with_user(self.user_wa_admin).model_id = self.env.ref('base.model_res_partner').id

        # try to change the model of the variable with x2many command
        with self.assertRaises(exceptions.ValidationError):
            self.env['whatsapp.template'].with_user(self.user_wa_admin).create({
                'body': "hello, I am from '{{1}}'.",
                'name': 'Test Template',
                'status': 'approved',
                'model_id': self.env.ref('base.model_res_users').id,
                'phone_field': 'phone_sanitized',
                'variable_ids': [(4, template.variable_ids.id)],
            })
