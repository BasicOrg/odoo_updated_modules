# -*- coding: utf-8 -*-
from .common import TestMxEdiCommon
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIInvoice(TestMxEdiCommon):

    @freeze_time('2017-01-01')
    def test_invoice_foreign_currency(self):
        invoice = self._create_invoice(currency_id=self.foreign_curr_1.id)

        # Change the currency to prove that the rate is computed based on the invoice
        self.currency_data['rates'].rate = 10

        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_foreign_currency')

    @freeze_time('2017-01-01')
    def test_invoice_misc_business_values(self):
        for move_type, output_file in (
            ('out_invoice', 'test_invoice_misc_business_values'),
            ('out_refund', 'test_credit_note_misc_business_values')
        ):
            with self.subTest(move_type=move_type):
                invoice = self._create_invoice(
                    invoice_incoterm_id=self.env.ref('account.incoterm_FCA').id,
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 2000.0,
                            'quantity': 5,
                            'discount': 20.0,
                        }),
                        # Ignored lines by the CFDI:
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 2000.0,
                            'quantity': 0.0,
                        }),
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 0.0,
                            'quantity': 10.0,
                        }),
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, output_file)

    @freeze_time('2017-01-01')
    def test_invoice_foreign_customer(self):
        invoice = self._create_invoice(partner_id=self.partner_us.id)
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_foreign_customer')

    @freeze_time('2017-01-01')
    def test_invoice_customer_with_no_country(self):
        self.partner_us.country_id = None
        invoice = self._create_invoice(partner_id=self.partner_us.id)
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_customer_with_no_country')

    @freeze_time('2017-01-01')
    def test_invoice_national_customer_to_public(self):
        invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_national_customer_to_public')

    @freeze_time('2017-01-01')
    def test_invoice_no_tax_breakdown(self):
        self.partner_mx.l10n_mx_edi_no_tax_breakdown = True
        invoice = self._create_invoice()
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_no_tax_breakdown')

    @freeze_time('2017-01-01')
    def test_invoice_group_of_taxes(self):
        tax_group = self.env['account.tax'].create({
            'name': 'tax_group',
            'amount_type': 'group',
            'amount': 0.0,
            'type_tax_use': 'sale',
            'children_tax_ids': [Command.set((self.tax_16 + self.tax_10_negative).ids)],
        })

        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 2000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [Command.set(tax_group.ids)],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_group_of_taxes')

    @freeze_time('2017-01-01')
    def test_invoice_tax_price_included(self):
        tax_16_incl = self.env['account.tax'].create({
            'name': 'tax_16',
            'amount_type': 'percent',
            'amount': 16,
            'type_tax_use': 'sale',
            'l10n_mx_factor_type': 'Tasa',
            'l10n_mx_tax_type': 'iva',
            'price_include': True,
            'include_base_amount': True,
        })

        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'quantity': 2,
                    'price_unit': 1160.0,
                    'tax_ids': [Command.set(tax_16_incl.ids)],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_tax_price_included')

    @freeze_time('2017-01-01')
    def test_invoice_full_discount_line(self):
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'discount': 100.0,
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_full_discount_line')

    @freeze_time('2017-01-01')
    def test_invoice_addenda(self):
        self.partner_mx.l10n_mx_edi_addenda = self.env['ir.ui.view'].create({
            'name': 'test_invoice_cfdi_addenda',
            'type': 'qweb',
            'arch': """
                <t t-name="l10n_mx_edi.test_invoice_cfdi_addenda">
                    <test info="this is an addenda"/>
                </t>
            """
        })

        invoice = self._create_invoice()
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_addenda')

    @freeze_time('2017-01-01')
    def test_invoice_negative_discount_line(self):
        self.env['ir.config_parameter'].sudo().create({
            'key': 'l10n_mx_edi.manage_invoice_negative_lines',
            'value': 'True',
        })

        discount_product = self.env['product.product'].create({
            'name': "discount_product",
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_01010101').id,
        })

        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 2000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
                Command.create({
                    'product_id': discount_product.id,
                    'price_unit': -2000.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_negative_discount_line')

    @freeze_time('2017-01-01')
    def test_invoice_tax_rounding(self):
        '''
        To pass validation by the PAC, the tax amounts reported for each invoice
        line need to fulfil the following two conditions:
        (1) The total tax amount must be equal to the sum of the tax amounts
            reported for each invoice line.
        (2) The tax amount reported for each line must be equal to
            (tax rate * base amount), rounded either up or down.
        For example, for the line with base = MXN 398.28, the exact tax amount
        would be 0.16 * 398.28 = 63.7248, so the acceptable values for the tax
        amount on that line are 63.72 and 63.73.
        For the line with base = 108.62, acceptable values are 17.37 and 17.38.
        For the line with base = 362.07, acceptable values are 57.93 and 57.94.
        For the lines with base = 31.9, acceptable values are 5.10 and 5.11.
        This test is deliberately crafted (thanks to the lines with base = 31.9)
        to introduce rounding errors which can fool some naive algorithms for
        allocating the total tax amount among tax lines (such as algorithms
        which allocate the total tax amount proportionately to the base amount).
        '''
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 398.28,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 108.62,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 362.07,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                })] + [
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 31.9,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
            ] * 12,
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_tax_rounding')

    @freeze_time('2017-01-01')
    def test_invoice_tax_objected_no_tax(self):
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_tax_objected_no_tax')

    @freeze_time('2017-01-01')
    def test_invoice_tax_objected_with_taxes(self):
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [],
                }),
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'discount': 100.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_tax_objected_with_taxes')

    @freeze_time('2017-01-01')
    def test_invoice_tax_objected_tax_exempted(self):
        self.partner_mx.l10n_mx_edi_no_tax_breakdown = True
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [],
                }),
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'discount': 100.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_tax_objected_tax_exempted')

    @freeze_time('2017-01-01')
    def test_invoice_tax_0_exento(self):
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.tax_0_exento.ids)],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_tax_0_exento')


    @freeze_time('2017-01-01')
    def test_invoice_tax_0_tasa(self):
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.tax_0.ids)],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_tax_0_tasa')

    @freeze_time('2017-01-01')
    def test_invoice_company_branch(self):
        self.env.company.write({
            'child_ids': [Command.create({
                'name': 'Branch A',
                'zip': '85120',
            })],
        })
        self.cr.precommit.run()  # load the CoA

        branch = self.env.company.child_ids
        invoice = self._create_invoice(company_id=branch.id)

        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_company_branch')

    @freeze_time('2017-01-05')
    def test_global_invoice(self):
        invoice1 = self._create_invoice(
            l10n_mx_edi_cfdi_to_public=True,
            invoice_date_due='2017-02-01',
            invoice_date='2017-01-02',
            date='2017-01-02',
            l10n_mx_edi_payment_method_id=self.payment_method_efectivo.id,
            invoice_line_ids=[
                Command.create({
                    # untaxed: 1000.0
                    # tax: 0.0
                    'product_id': self.product.id,
                    'tax_ids': [],
                }),
                # Both following lines will be aggregated:
                Command.create({
                    # untaxed: 8000.0
                    # tax: 1280.0
                    'product_id': self.product.id,
                    'price_unit': 2000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
                Command.create({
                    # untaxed: 10000.0
                    # tax: 1600.0
                    'product_id': self.product.id,
                    'quantity': 10,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
            ],
        )
        invoice2 = self._create_invoice(
            l10n_mx_edi_cfdi_to_public=True,
            invoice_date_due='2017-03-01',
            invoice_date='2017-01-03',
            date='2017-01-05',
            l10n_mx_edi_payment_method_id=self.payment_method_efectivo.id,
            invoice_line_ids=[
                Command.create({
                    # untaxed: 1800.0
                    # tax: 288.0
                    'product_id': self.product.id,
                    'quantity': 2,
                    'discount': 10.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
                Command.create({
                    # untaxed: 1000.0
                    # tax: 0.0
                    'product_id': self.product.id,
                    'tax_ids': [Command.set(self.tax_0_exento.ids)],
                }),
                Command.create({
                    # untaxed: 1000.0
                    # tax: 80.0
                    'product_id': self.product.id,
                    'tax_ids': [Command.set(self.tax_8_ieps.ids)],
                }),
                Command.create({
                    # untaxed: 1000.0
                    # tax: 80.0
                    'product_id': self.product.id,
                    'tax_ids': [Command.set((self.tax_0_exento + self.tax_8_ieps).ids)],
                }),
            ],
        )
        invoices = invoice1 + invoice2

        with self.with_mocked_pac_sign_success():
            invoices._l10n_mx_edi_cfdi_global_invoice_try_send()
        self._assert_global_invoice_cfdi_from_invoices(invoices, 'test_global_invoice')

    @freeze_time('2017-01-05')
    def test_global_invoice_0_iva_tax_only(self):
        invoice1 = self._create_invoice(
            l10n_mx_edi_cfdi_to_public=True,
            l10n_mx_edi_payment_method_id=self.payment_method_efectivo.id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'tax_ids': [Command.set(self.tax_0.ids)],
                }),
            ],
        )
        invoice2 = self._create_invoice(
            l10n_mx_edi_cfdi_to_public=True,
            l10n_mx_edi_payment_method_id=self.payment_method_efectivo.id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'tax_ids': [Command.set(self.tax_0.ids)],
                }),
            ],
        )
        invoices = invoice1 + invoice2

        with self.with_mocked_pac_sign_success():
            invoices._l10n_mx_edi_cfdi_global_invoice_try_send()
        self._assert_global_invoice_cfdi_from_invoices(invoices, 'test_global_invoice_0_iva_tax_only')

    @freeze_time('2017-01-01')
    def test_invoice_then_refund(self):
        # Create an invoice then sign it.
        invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
        with self.with_mocked_pac_sign_success():
            self.env['account.move.send']\
                .with_context(active_model=invoice._name, active_ids=invoice.ids)\
                .create({})\
                .action_send_and_print()
        self._assert_invoice_cfdi(invoice, 'test_invoice_then_refund_1')

        # You are no longer able to create a global invoice.
        with self.assertRaises(UserError):
            self.env['l10n_mx_edi.global_invoice.create']\
                .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({})

        # Create a refund.
        results = self.env['account.move.reversal']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'date': '2017-01-01',
                'reason': "turlututu",
                'journal_id': invoice.journal_id.id,
            })\
            .refund_moves()
        refund = self.env['account.move'].browse(results['res_id'])
        refund.auto_post = 'no'
        refund.action_post()

        # You can't make a global invoice for it.
        with self.assertRaises(UserError):
            self.env['l10n_mx_edi.global_invoice.create']\
                .with_context(refund.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({})

        # Create the CFDI and sign it.
        with self.with_mocked_pac_sign_success():
            self.env['account.move.send']\
                .with_context(active_model=refund._name, active_ids=refund.ids)\
                .create({})\
                .action_send_and_print()
        self._assert_invoice_cfdi(refund, 'test_invoice_then_refund_2')
        self.assertRecordValues(refund, [{
            'l10n_mx_edi_cfdi_origin': f'01|{invoice.l10n_mx_edi_cfdi_uuid}',
        }])

    @freeze_time('2017-01-01')
    def test_global_invoice_then_refund(self):
        # Create a global invoice and sign it.
        invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
        with self.with_mocked_pac_sign_success():
            self.env['l10n_mx_edi.global_invoice.create']\
                .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({})\
                .action_create_global_invoice()
        self._assert_global_invoice_cfdi_from_invoices(invoice, 'test_global_invoice_then_refund_1')

        # You are not able to create an invoice for it.
        wizard = self.env['account.move.send']\
            .with_context(active_model=invoice._name, active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard, [{'l10n_mx_edi_enable_cfdi': False}])

        # Refund the invoice.
        results = self.env['account.move.reversal']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'date': '2017-01-01',
                'reason': "turlututu",
                'journal_id': invoice.journal_id.id,
            })\
            .refund_moves()
        refund = self.env['account.move'].browse(results['res_id'])
        refund.auto_post = 'no'
        refund.action_post()

        # You can't do a global invoice for a refund
        with self.assertRaises(UserError):
            self.env['l10n_mx_edi.global_invoice.create']\
                .with_context(refund.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({})

        # Sign the refund.
        with self.with_mocked_pac_sign_success():
            self.env['account.move.send']\
                .with_context(active_model=refund._name, active_ids=refund.ids)\
                .create({})\
                .action_send_and_print()
        self._assert_invoice_cfdi(refund, 'test_global_invoice_then_refund_2')

    @freeze_time('2017-01-01')
    def test_invoice_pos(self):
        # Trigger an error when generating the CFDI
        self.product.unspsc_code_id = False
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.tax_0.ids)],
                }),
            ],
        )
        template = self.env.ref(invoice._get_mail_template())
        invoice.with_context(skip_invoice_sync=True)._generate_pdf_and_send_invoice(template, force_synchronous=True, allow_fallback_pdf=True)
        self.assertFalse(invoice.invoice_pdf_report_id, "invoice_pdf_report_id shouldn't be set with the proforma PDF.")

    @freeze_time('2017-01-01')
    def test_import_invoice_cfdi(self):
        # Invoice with payment policy = PUE, otherwise 'FormaPago' (payment method) is set to '99' ('Por Definir')
        # and the initial payment method cannot be backtracked at import
        invoice = self._create_invoice(
            invoice_date_due='2017-01-01',  # PUE
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
            ],
        )
        # Modify the vat, otherwise there are 2 partners with the same vat
        invoice.partner_id.vat = "XIA190128J62"

        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

        new_invoice = self._upload_document_on_journal(
            journal=self.company_data['default_journal_sale'],
            content=invoice.l10n_mx_edi_document_ids.attachment_id.raw.decode(),
            filename=invoice.l10n_mx_edi_document_ids.attachment_id.name,
        )

        # Check the newly created invoice
        expected_vals, expected_line_vals = self._export_move_vals(invoice)
        self.assertRecordValues(new_invoice, [expected_vals])
        self.assertRecordValues(new_invoice.invoice_line_ids, expected_line_vals)

        # the state of the document should be "Sent"
        self.assertEqual(new_invoice.l10n_mx_edi_invoice_document_ids.state, "invoice_sent")
        new_invoice.action_post()
        # the "Request Cancel" button should appear after posting
        self.assertTrue(new_invoice.need_cancel_request)
        # the "Update SAT" button should appear
        self.assertTrue(new_invoice.l10n_mx_edi_update_sat_needed)

    @freeze_time('2017-01-01')
    def test_import_bill_cfdi(self):
        # Invoice with payment policy = PUE, otherwise 'FormaPago' (payment method) is set to '99' ('Por Definir')
        # and the initial payment method cannot be backtracked at import
        invoice = self._create_invoice(
            invoice_date_due='2017-01-01',  # PUE
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }),
            ],
        )

        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

        new_bill = self._upload_document_on_journal(
            journal=self.company_data['default_journal_purchase'],
            content=invoice.l10n_mx_edi_document_ids.attachment_id.raw.decode(),
            filename=invoice.l10n_mx_edi_document_ids.attachment_id.name,
        )

        # Check the newly created bill
        expected_vals, expected_line_vals = self._export_move_vals(invoice)
        expected_vals.update({
            'partner_id': invoice.company_id.partner_id.id,
            'l10n_mx_edi_payment_policy': False,
        })
        self.assertRecordValues(new_bill, [expected_vals])
        expected_line_vals[0]['tax_ids'] = self.env['account.chart.template'].ref('tax14').ids
        self.assertRecordValues(new_bill.invoice_line_ids, expected_line_vals)

        # the state of the document should be "Sent"
        self.assertEqual(new_bill.l10n_mx_edi_invoice_document_ids.state, "invoice_received")
        # the "Update SAT" button should appear continuously (after posting)
        new_bill.action_post()
        self.assertTrue(new_bill.l10n_mx_edi_update_sat_needed)
        with self.with_mocked_sat_call(lambda _x: 'valid'):
            new_bill.l10n_mx_edi_cfdi_try_sat()
        self.assertTrue(new_bill.l10n_mx_edi_update_sat_needed)
