# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.whatsapp.tests.common import WhatsAppCommon, MockIncomingWhatsApp
from odoo.tests import tagged, users


@tagged('whatsapp', 'post_install', '-at_install')
class WhatsAppWebhookCase(WhatsAppCommon, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_salesperson = mail_new_test_user(
            cls.env,
            groups="base.group_user",
            login="user_salesperson",
        )

        cls.user_salesperson_2 = mail_new_test_user(
            cls.env,
            groups="base.group_user",
            login="user_salesperson_2",
        )

        cls.user_salesperson_3 = mail_new_test_user(
            cls.env,
            groups="base.group_user",
            login="user_salesperson_3",
        )

        cls.whatsapp_template = cls.env['whatsapp.template'].create({
            'body': 'Hello World',
            'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
            'name': 'WhatsApp Template',
            'template_name': 'whatsapp_template',  # not computed because pre-approved
            'status': 'approved',
            'wa_account_id': cls.whatsapp_account.id,
        })

    def test_blocklist_message(self):
        """ Test the automatic blocklist mechanism when receiving 'stop'. """
        self._receive_whatsapp_message(
            self.whatsapp_account,
            "Hello, how can remove my number from your WhatsApp listing?",
            "32499123456",
        )

        discuss_channel = self.assertWhatsAppChannel("32499123456")

        with self.mockWhatsappGateway():
            discuss_channel.message_post(
                body="Hello, you can just send 'stop' to this number.",
                message_type="whatsapp_message",
            )

        self._receive_whatsapp_message(self.whatsapp_account, "Stop", "32499123456")

        # at this point, we should have 3 mail.messages and whatsapp.messages
        self.assertEqual(len(discuss_channel.message_ids), 3)
        whatsapp_messages = self.env["whatsapp.message"].search([
            ("mail_message_id", "in", discuss_channel.message_ids.ids)
        ])
        self.assertEqual(len(whatsapp_messages), 3)

        # make sure we have a matching entry in the blacklist table
        blacklist_record = self.env["phone.blacklist"].search([("number", "=", "+32499123456")])
        self.assertTrue(bool(blacklist_record))

        # post a regular message: should not send through WhatsApp
        with self.mockWhatsappGateway():
            not_sent_message = discuss_channel.message_post(
                body="Hello, Did it work?",
                message_type="whatsapp_message",
            )
        self.assertWAMessage("error", fields_values={
            "failure_type": "blacklisted",
            "mail_message_id": not_sent_message,
            "mobile_number": "+32499123456",
        })

        # attempt to send a template: should not send through WhatsApp
        test_record = self.env["whatsapp.test.base"].create({
            "country_id": self.env.ref("base.be").id,
            "name": "Test Record",
            "phone": "+32499123456",
        })

        test_template = self.env["whatsapp.template"].create({
            "body": "Hello World",
            "model_id": self.env["ir.model"]._get_id("whatsapp.test.base"),
            "name": "Hello World Template",
            "status": "approved",
        })

        composer = self._instanciate_wa_composer_from_records(test_template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessage("error", fields_values={
            "failure_type": "blacklisted",
            "mobile_number": "+32499123456",
        })

        # remove from blacklist, make sure we can send WhatsApp messages again
        self._receive_whatsapp_message(
            self.whatsapp_account,
            "Hello, I would like to receive messages again.",
            "32499123456",
        )
        self.assertFalse(self.env["phone.blacklist"].search([("number", "=", "+32499123456")]))
        with self.mockWhatsappGateway():
            sent_message = discuss_channel.message_post(
                body="Welcome back!",
                message_type="whatsapp_message",
            )
        self.assertWAMessage("sent", fields_values={
            "failure_type": False,
            "mail_message_id": sent_message,
            "mobile_number": "+32499123456",
        })

    @users('user_wa_admin')
    def test_conversation_match(self):
        """ Test a conversation with multiple channels and messages. Received
        messages should all be linked to the document if there is a suitable
        message sent within the 15 days time frame (see '_find_active_channel').
        If we send a message in reply to a specific one, we should find the
        discuss message of that channel and use that channel instead. """
        self._receive_whatsapp_message(self.whatsapp_account, "Hey there", "32499123456")
        no_document_discuss_channel = self.assertWhatsAppChannel("32499123456")

        with self.mockWhatsappGateway():
            operator_message = no_document_discuss_channel.message_post(
                body="Hello, feel free to ask any questions you may have!",
                message_type="whatsapp_message"
            )
        self.assertEqual(len(no_document_discuss_channel.message_ids), 2)
        self.assertWAMessage("sent", fields_values={
            "mail_message_id": operator_message,
        })
        operator_whatsapp_message = self._new_wa_msg

        # send using template -> replies will create a new channel linked to the document
        test_record = self.env['whatsapp.test.base'].create({
            'country_id': self.env.ref('base.be').id,
            'name': 'Test Record',
            'phone': '+32499123456',
        })
        composer = self._instanciate_wa_composer_from_records(self.whatsapp_template.with_user(self.env.user), test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        self._receive_whatsapp_message(
            self.whatsapp_account, "Hello, why are you sending me this?", "32499123456",
        )

        document_discuss_channel = self.env["discuss.channel"].search([
            ("whatsapp_number", "=", "32499123456"),
            ("id", "!=", no_document_discuss_channel.id)])
        self.assertTrue(bool(document_discuss_channel))
        self.assertEqual(len(document_discuss_channel.message_ids), 2)

        with self.mockWhatsappGateway():
            document_discuss_channel.message_post(
                body="Hello, sorry it was a mistake.",
                message_type="whatsapp_message")

        # message should be correctly associated to existing discuss conversation
        self.assertEqual(len(document_discuss_channel.message_ids), 3)

        # reply to the original discussion (the one not linked to a document)
        # -> should correctly match the associated discuss channel
        self._receive_whatsapp_message(
            self.whatsapp_account,
            "You mentioned I could ask questions here, can you explain your products please?",
            "32499123456",
            additional_message_values={"context": {"id": operator_whatsapp_message.msg_uid}}
        )
        no_document_whatsapp_messages = no_document_discuss_channel.message_ids.filtered(
            lambda m: m.message_type == 'whatsapp_message')
        self.assertEqual(len(no_document_whatsapp_messages), 3,
                         'Should be customer init + operator response + customer response')
        self.assertEqual(len(no_document_discuss_channel.message_ids), 4,
                         'Should be a regular message mentioning a template was sent to the customer')
        document_whatsapp_messages = no_document_discuss_channel.message_ids.filtered(
            lambda m: m.message_type == 'whatsapp_message')
        self.assertEqual(len(document_discuss_channel.message_ids), 3,
                         'Should be template + customer response + operator response')
        self.assertEqual(len(document_whatsapp_messages), 3,
                         'There should only be whatsapp messages in the latest template conversations')

    def test_receive_no_document(self):
        """ Receive a message that is not linked to any document. It should
        create a 'standalone' channel with the whatsapp account notified people. """
        self._receive_whatsapp_message(
            self.whatsapp_account, "Hello, I have a question please.", "32499123456"
        )
        discuss_channel = self.assertWhatsAppChannel("32499123456")

        channel_message = discuss_channel.message_ids[0]
        self.assertEqual(channel_message.body, "<p>Hello, I have a question please.</p>")

        self.assertIn(self.user_wa_admin.partner_id, discuss_channel.channel_partner_ids)
        customer_partner = discuss_channel.channel_partner_ids - self.user_wa_admin.partner_id
        self.assertEqual(len(customer_partner), 1)
        self.assertEqual(customer_partner.name, "+32 499 12 34 56")

    def test_responsible_with_template(self):
        """ Test various use cases of receiving a message that is linked to a
        template. Main idea is to check who is added to notified people. """
        test_template = self.whatsapp_template.copy()
        test_template.write({
            'model_id': self.env['ir.model']._get_id('whatsapp.test.responsible'),
            'name': 'Responsible Template',
            'template_name': 'responsible_template',
            'status': 'approved',
        })
        test_template_no_record = test_template.copy()
        test_template_no_record.write({
            'model_id': self.env['ir.model']._get_id('whatsapp.test.nothread'),
            'name': 'No Responsible Template',
            'template_name': 'no_responsible_template',
            'status': 'approved',
        })

        test_record = self.env['whatsapp.test.responsible'].create({
            'name': 'Test Record',
            'phone': '+32 497 99 99 99',
        })
        test_record_no_responsible = self.env['whatsapp.test.nothread'].create({
            'name': 'Test Record No Responsible',
            'phone': '+32 497 11 11 11',
        })

        expected_responsible = self.user_wa_admin
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by superuser (e.g: automated process)
            # record was created/written on by superuser
            # there is no method to get a responsible
            # -> should be the last fallback: 'account.notify_user_ids'
            self._test_responsible_with_template(
                test_record_no_responsible,
                expected_responsible,
                test_template_no_record)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        expected_responsible = self.user_wa_admin
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by superuser (e.g: automated process)
            # record was created/written on by superuser
            # -> should be the last fallback: 'account.notify_user_ids'
            self._test_responsible_with_template(
                test_record,
                expected_responsible,
                test_template)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        test_record.with_user(self.user_salesperson).write({'name': 'Edited name'})
        expected_responsible = self.user_salesperson
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by superuser (e.g: automated process)
            # record was written on by user_salesperson
            # -> should be the write_uid fallback: 'user_salesperson'
            self._test_responsible_with_template(
                test_record,
                expected_responsible,
                test_template)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        expected_responsible = self.user_salesperson_2
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by user_salesperson_2
            # -> should be the author fallback: 'user_salesperson_2'
            self._test_responsible_with_template(
                test_record,
                expected_responsible,
                test_template,
                context_user=self.user_salesperson_2)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        expected_responsible = self.user_salesperson_3
        test_record.write({'user_id': self.user_salesperson_3.id})
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by superuser (e.g: automated process)
            # record is owned by user_salesperson_3
            # -> should be the owner (user_id) fallback: 'user_salesperson_3'
            self._test_responsible_with_template(
                test_record,
                expected_responsible,
                test_template)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        expected_responsible = self.user_salesperson_2 | self.user_salesperson_3
        test_record.write({'user_id': self.user_salesperson_3.id})
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by user_salesperson_2
            # record is owned by user_salesperson_3
            # -> should be the owner (user_id) + sender: 'user_salesperson_2' + 'user_salesperson_3'
            self._test_responsible_with_template(
                test_record,
                expected_responsible,
                test_template,
                context_user=self.user_salesperson_2)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels
        test_record.user_id = False  # reset responsible user

        expected_responsible = self.user_salesperson | self.user_salesperson_2 | self.user_salesperson_3
        test_record.write({'user_ids': (self.user_salesperson | self.user_salesperson_3).ids})
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by user_salesperson_2
            # record is owned by user_salesperson AND user_salesperson_3
            # -> should be the owners (user_ids) + sender:
            # 'user_salesperson' + 'user_salesperson_2' + 'user_salesperson_3'
            self._test_responsible_with_template(
                test_record,
                expected_responsible,
                test_template,
                context_user=self.user_salesperson_2)

    def _test_responsible_with_template(self, test_record, expected_responsible, template_id, context_user=False):
        """ Receive a message that is linked to a template sent on test_record.
        Should create a channel linked to that document, using the 'expected_responsible'
        as members. """
        # assumes valid phone numbers with country code
        customer_phone_number = test_record.phone.lstrip('+').replace(' ', '')

        with self.mockWhatsappGateway():
            composer = self._instanciate_wa_composer_from_records(template_id, test_record, with_user=context_user)
            composer._send_whatsapp_template()

            self._receive_whatsapp_message(
                self.whatsapp_account,
                "Hello, I have already paid this.",
                customer_phone_number,
            )

        discuss_channel = self.env["discuss.channel"].search([
            ("whatsapp_number", "=", customer_phone_number)])
        self.assertTrue(bool(discuss_channel))
        self.assertEqual(len(discuss_channel.message_ids), 2)
        channel_messages = discuss_channel.message_ids.sorted(lambda message: message.id)
        context_message = channel_messages[0]
        self.assertIn(f"Related {self.env['ir.model']._get(test_record._name).display_name}:", context_message.body)
        self.assertIn(test_record.name, context_message.body)
        self.assertIn(f"/web#model={test_record._name}&amp;id={test_record.id}", context_message.body,
                      "Should contain a link to the context record")

        customer_message = channel_messages[1]
        self.assertEqual(customer_message.body, "<p>Hello, I have already paid this.</p>")

        for user in expected_responsible:
            self.assertIn(user.partner_id, discuss_channel.channel_partner_ids)
        customer_partner = discuss_channel.channel_partner_ids - expected_responsible.partner_id
        self.assertEqual(len(customer_partner), 1)
        self.assertEqual(customer_partner.name, test_record.phone)
