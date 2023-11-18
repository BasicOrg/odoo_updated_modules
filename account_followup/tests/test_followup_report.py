# -*- coding: utf-8 -*-
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo import Command


@tagged('post_install', '-at_install')
class TestAccountFollowupReports(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_a.email = 'partner_a@mypartners.xyz'

    def test_followup_report(self):
        ''' Test report lines when printing the follow-up report. '''
        # Init options.
        report = self.env['account.followup.report']
        options = {
            'partner_id': self.partner_a.id,
            'multi_currency': True,
        }

        # 2016-01-01: First invoice, partially paid.

        invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice_1.action_post()

        payment_1 = self.env['account.move'].create({
            # pylint: disable=C0326
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 200.0,    'account_id': self.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'account_id': self.company_data['default_journal_bank'].default_account_id.id}),
            ],
        })
        payment_1.action_post()

        (payment_1 + invoice_1).line_ids\
            .filtered(lambda line: line.account_id == self.company_data['default_account_receivable'])\
            .reconcile()

        with freeze_time('2016-01-01'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_followup_report_lines(options),
                #   Name                                    Date,           Due Date,       Doc.      Total Due
                [   0,                                      1,              2,              3,        5],
                [
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',       300.0),
                    ('',                                    '',             '',             '',       300.0),
                ],
                options,
            )

        # 2016-01-05: Credit note due at 2016-01-10.

        invoice_2 = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2016-01-05',
            'invoice_date_due': '2016-01-10',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': False,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 200,
                'tax_ids': [],
            })]
        })
        invoice_2.action_post()

        with freeze_time('2016-01-05'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_followup_report_lines(options),
                #   Name                                    Date,           Due Date,       Doc.      Total Due
                [   0,                                      1,              2,              3,        5],
                [
                    ('RINV/2016/00001',                     '01/05/2016',   '01/10/2016',   '',      -200.0),
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',       300.0),
                    ('',                                    '',             '',             '',       100.0),
                    ('',                                    '',             '',             '',       300.0),
                ],
                options,
            )

        # 2016-01-15: Draft invoice + previous credit note reached the date_maturity + first invoice reached the delay
        # of the first followup level.

        self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2016-01-15',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 1000,
                'tax_ids': [],
            })]
        })

        with freeze_time('2016-01-15'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_followup_report_lines(options),
                #   Name                                    Date,           Due Date,       Doc.      Total Due
                [   0,                                      1,              2,              3,        5],
                [
                    ('RINV/2016/00001',                     '01/05/2016',   '01/10/2016',   '',      -200.0),
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',       300.0),
                    ('',                                    '',             '',             '',       100.0),
                    ('',                                    '',             '',             '',       100.0),
                ],
                options,
            )

        # Trigger the followup report notice.

        invoice_attachments = self.env['ir.attachment']
        for invoice in invoice_1 + invoice_2:
            invoice_attachment = self.env['ir.attachment'].create({
                'name': 'some_attachment.pdf',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'datas': 'test',
                'type': 'binary',
            })
            invoice_attachments += invoice_attachment
            invoice._message_set_main_attachment_id(invoice_attachment.ids)

        self.partner_a._compute_unpaid_invoices()
        options['attachment_ids'] = invoice_attachments.ids
        with patch.object(type(self.env['mail.mail']), 'unlink', lambda self: None):
            self.env['account.followup.report']._send_email(options)
        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', self.partner_a.id)]).attachment_ids

        self.assertEqual(invoice_attachments, sent_attachments)

        attachaments_domain = [('attachment_ids', '=', attachment.id) for attachment in invoice_attachments]
        mail = self.env['mail.mail'].search([('recipient_ids', '=', self.partner_a.id)] + attachaments_domain)
        self.assertTrue(mail, "A payment reminder email should have been sent.")

    def test_followup_report_address_1(self):
        ''' Test child contact priorities: the company will be used when there is no followup or billing contacts
        '''

        Partner = self.env['res.partner']
        self.partner_a.is_company = True
        options = {
            'partner_id': self.partner_a.id,
        }

        child_partner = Partner.create({
            'name': "Child contact",
            'type': "contact",
            'parent_id': self.partner_a.id,
        })

        mail = self.env['mail.mail'].search([('recipient_ids', '=', self.partner_a.id)])
        self.init_invoice('out_invoice', partner=child_partner, invoice_date='2016-01-01', amounts=[500], post=True)
        self.partner_a._compute_unpaid_invoices()
        with patch.object(type(self.env['mail.mail']), 'unlink', lambda self: None):
            self.env['account.followup.report']._send_email(options)

        mail = self.env['mail.mail'].search([('recipient_ids', '=', self.partner_a.id)])
        self.assertTrue(mail, "The payment reminder email should have been sent to the company.")

    def test_followup_report_address_2(self):
        ''' Test child contact priorities: the follow up contact will be preferred over the billing contact
        '''

        Partner = self.env['res.partner']
        self.partner_a.is_company = True
        options = {
            'partner_id': self.partner_a.id,
        }

        # Testing followup sent to billing address if used in invoice

        child_partner = Partner.create({
            'name': "Child contact",
            'type': "contact",
            'parent_id': self.partner_a.id,
        })
        invoice_partner = Partner.create({
            'name' : "Child contact invoice",
            'type' : "invoice",
            'email' : "test-invoice@example.com",
            'parent_id': child_partner.id,
        })

        self.init_invoice('out_invoice', partner=invoice_partner, invoice_date='2016-01-01', amounts=[500], post=True)

        self.partner_a._compute_unpaid_invoices()
        with patch.object(type(self.env['mail.mail']), 'unlink', lambda self: None):
            self.env['account.followup.report']._send_email(options)

        mail = self.env['mail.mail'].search([('recipient_ids', '=', invoice_partner.id)])
        self.assertTrue(mail, "The payment reminder email should have been sent to the invoice partner.")
        mail.unlink()

        # Testing followup partner priority

        followup_partner = Partner.create({
            'name' : "Child contact followup",
            'type' : "followup",
            'email' : "test-followup@example.com",
            'parent_id': self.partner_a.id,
        })

        self.partner_a._compute_unpaid_invoices()
        with patch.object(type(self.env['mail.mail']), 'unlink', lambda self: None):
            self.env['account.followup.report']._send_email(options)

        mail = self.env['mail.mail'].search([('recipient_ids', '=', followup_partner.id)])
        self.assertTrue(mail, "The payment reminder email should have been sent to the followup partner.")

    def test_followup_invoice_no_amount(self):
        # Init options.
        report = self.env['account.followup.report']
        options = {
            'partner_id': self.partner_a.id,
        }

        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2022-01-01',
            'invoice_line_ids': [
                (0, 0, {'quantity': 0, 'price_unit': 30}),
            ],
        })
        invoice_move.action_post()

        lines = report._get_followup_report_lines(options)
        self.assertEqual(len(lines), 0, "There should be no line displayed")

    def test_negative_followup_report(self):
        ''' Test negative or null followup reports: if a contact has an overdue invoice but has a negative of null total due, no action is needed.
        '''
        self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': False,
        })
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        }).action_post()

        self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2016-01-15',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 300,
                'tax_ids': [],
            })]
        }).action_post()
        self.assertEqual(self.partner_a.total_due, 200)
        self.assertEqual(self.partner_a.followup_status, 'in_need_of_action')

        self.env['account.payment'].create({
            'move_type': 'inbound',
            'partner_id': self.partner_a.id,
            'amount': 400,
        }).action_post()
        self.assertEqual(self.partner_a.total_due, -200)
        self.assertEqual(self.partner_a.followup_status, 'no_action_needed')
