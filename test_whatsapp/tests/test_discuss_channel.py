# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.whatsapp.tests.common import WhatsAppCommon, MockIncomingWhatsApp
from odoo.tests import tagged, users


@tagged('wa_message')
class DiscussChannel(WhatsAppCommon, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.whatsapp_template = cls.env['whatsapp.template'].create({
            'body': 'Hello World',
            'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
            'name': 'WhatsApp Template',
            'template_name': 'whatsapp_template',  # not computed because pre-approved
            'status': 'approved',
            'wa_account_id': cls.whatsapp_account.id,
        })

    @users('user_wa_admin')
    def test_channel_validity_date(self):
        """ Ensure the validity date of a whatsapp channel is only affected by
        messages sent by the whatsapp recipient. """
        template = self.whatsapp_template.with_user(self.env.user)
        test_record = self.env['whatsapp.test.base'].create({
            'country_id': self.env.ref('base.be').id,
            'name': 'Test Record',
            'phone': '+32499123456',
        })

        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        self._receive_whatsapp_message(self.whatsapp_account, 'Hello', '32499123456')

        discuss_channel = self.env["discuss.channel"].search([("whatsapp_number", "=", "32499123456")])
        self.assertTrue(discuss_channel.whatsapp_channel_valid_until)
        first_valid_date = discuss_channel.whatsapp_channel_valid_until

        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        second_valid_date = discuss_channel.whatsapp_channel_valid_until

        self.assertEqual(first_valid_date, second_valid_date)
