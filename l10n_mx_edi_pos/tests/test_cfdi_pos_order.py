from .common import TestMxEdiPosCommon

from odoo.exceptions import UserError
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIPosOrder(TestMxEdiPosCommon):

    @freeze_time('2017-01-01')
    def test_global_invoice_workflow(self):
        with self.with_pos_session() as _session:
            order1 = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 1)],
                'payments': [(self.bank_pm1, 1160.0)],
            })
            order2 = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 1)],
                'payments': [(self.bank_pm1, 1160.0)],
            })
            orders = order1 + order2

            with self.with_mocked_pac_sign_error():
                orders._l10n_mx_edi_cfdi_global_invoice_try_send()
            self.assertRecordValues(orders.l10n_mx_edi_document_ids, [
                {
                    'pos_order_ids': orders.ids,
                    'state': 'ginvoice_sent_failed',
                    'sat_state': False,
                    'cancel_button_needed': False,
                    'retry_button_needed': True,
                },
            ])

            # Successfully create the global invoice.
            with self.with_mocked_pac_sign_success():
                orders._l10n_mx_edi_cfdi_global_invoice_try_send()
            sent_doc_values = {
                'pos_order_ids': orders.ids,
                'message': False,
                'state': 'ginvoice_sent',
                'sat_state': 'not_defined',
                'cancel_button_needed': True,
                'retry_button_needed': False,
            }
            self.assertRecordValues(orders.l10n_mx_edi_document_ids, [sent_doc_values])
            self.assertTrue(orders.l10n_mx_edi_document_ids.attachment_id)
            self.assertRecordValues(orders, [{
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_state': 'global_sent',
            }] * 2)

            with self.with_mocked_sat_call(lambda _x: 'valid'):
                self.env['l10n_mx_edi.document']._fetch_and_update_sat_status(
                    extra_domain=[('id', '=', orders.l10n_mx_edi_document_ids.id)]
                )
            sent_doc_values['sat_state'] = 'valid'
            self.assertRecordValues(orders.l10n_mx_edi_document_ids, [sent_doc_values])

    @freeze_time('2017-01-01')
    def test_global_invoice_misc_business_values(self):
        """ Create orders for anonymous customers and create Global Invoice. """
        product1 = self._create_product(taxes_id=[])
        product2 = self._create_product(lst_price=2000.0)
        product3 = self.product

        with self.with_pos_session() as _session:
            order1 = self._create_order({
                'pos_order_lines_ui_args': [
                    (product1, 1),
                    (product2, 5, 20.0),
                    (product3, 10),
                ],
                'payments': [(self.bank_pm1, 21880.0)],
            })
            order2 = self._create_order({
                'pos_order_lines_ui_args': [
                    (product3, 2, 10.0),
                ],
                'payments': [(self.bank_pm1, 2088.0)],
            })

        orders = order1 + order2
        with self.with_mocked_pac_sign_success():
            self.env['l10n_mx_edi.global_invoice.create'] \
                .with_context(orders.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({}) \
                .action_create_global_invoice()
        self._assert_global_invoice_cfdi_from_orders(orders, 'test_global_invoice_misc_business_values')

    @freeze_time('2017-01-01')
    def test_invoiced_order_then_refund(self):
        with self.with_pos_session() as _session:
            # Invoice an order, then sign it.
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 10)],
                'payments': [(self.bank_pm1, 11600.0)],
                'customer': self.partner_mx,
                'is_invoiced': True,
            })
            invoice = order.account_move
            with self.with_mocked_pac_sign_success():
                self.env['account.move.send'] \
                    .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                    .create({}) \
                    .action_send_and_print()
            self._assert_invoice_cfdi(invoice, 'test_invoiced_order_then_refund_1')

        # You are no longer able to create a global invoice for it.
        with self.assertRaises(UserError):
            self.env['l10n_mx_edi.global_invoice.create'] \
                .with_context(order.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({})
        with self.assertRaises(UserError):
            self.env['l10n_mx_edi.global_invoice.create'] \
                .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({})

        with self.with_pos_session() as _session:
            # Invoice the refund order, then sign it.
            refund_order = self._create_order({
                'pos_order_lines_ui_args': [{
                    'product': self.product,
                    'quantity': -10,
                    'refunded_orderline_id': order.lines.id,
                }],
                'payments': [(self.bank_pm1, -11600.0)],
                'customer': self.partner_mx,
                'is_invoiced': True,
            })
            refund = refund_order.account_move

        # You can't make a global invoice for it.
        with self.assertRaises(UserError):
            self.env['l10n_mx_edi.global_invoice.create'] \
                .with_context(refund.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({})

        # Create the CFDI and sign it.
        with self.with_mocked_pac_sign_success():
            self.env['account.move.send'] \
                .with_context(active_model=refund._name, active_ids=refund.ids) \
                .create({})\
                .action_send_and_print()
        self._assert_invoice_cfdi(refund, 'test_invoiced_order_then_refund_2')
        self.assertRecordValues(refund, [{
            'l10n_mx_edi_cfdi_origin': f'03|{invoice.l10n_mx_edi_cfdi_uuid}',
        }])

    @freeze_time('2017-01-01')
    def test_global_invoiced_order_then_refund_then_invoiced(self):
        with self.with_pos_session() as _session:
            # Create an order, then make a global invoice and sign it.
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 10)],
                'payments': [(self.bank_pm1, 11600.0)],
                'customer': self.partner_mx,
                'uid': '0001',
            })

        with self.with_mocked_pac_sign_success():
            self.env['l10n_mx_edi.global_invoice.create'] \
                .with_context(order.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({}) \
                .action_create_global_invoice()
        self._assert_global_invoice_cfdi_from_orders(order, 'test_global_invoiced_order_then_refund_then_invoiced_1')
        self.assertRecordValues(order, [{'l10n_mx_edi_cfdi_state': 'global_sent'}])

        order_sent_doc_values = {
            'pos_order_ids': order.ids,
            'state': 'ginvoice_sent',
        }
        self.assertRecordValues(order.l10n_mx_edi_document_ids, [order_sent_doc_values])

        with self.with_pos_session() as _session, self.with_mocked_pac_sign_success():
            # Refund the order.
            refund_order = order._refund()

        self._assert_order_cfdi(refund_order, 'test_global_invoiced_order_then_refund_then_invoiced_2')
        self.assertRecordValues(refund_order, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        refund_sent_doc_values = {
            'pos_order_ids': refund_order.ids,
            'state': 'invoice_sent',
        }
        self.assertRecordValues(refund_order.l10n_mx_edi_document_ids, [refund_sent_doc_values])

        # You can't make a global invoice for it since a document has already been generated automatically.
        with self.assertRaises(UserError):
            self.env['l10n_mx_edi.global_invoice.create'] \
                .with_context(refund_order.l10n_mx_edi_action_create_global_invoice()['context']) \
                .create({})

        # You are not able to create an invoice for it.
        with self.assertRaises(UserError):
            refund_order.action_pos_order_invoice()

        # Invoice.
        with self.with_pos_session() as _session, self.with_mocked_pac_sign_success():
            order.action_pos_order_invoice()

            # Sign it.
            invoice = order.account_move
            self.env['account.move.send'] \
                .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                .create({}) \
                .action_send_and_print()
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Nothing changed on the order.
        self.assertRecordValues(order.l10n_mx_edi_document_ids, [order_sent_doc_values])

    @freeze_time('2017-01-01')
    def test_global_invoiced_order_then_invoiced_then_refund_then_cancel_it(self):
        with self.with_pos_session() as _session:
            # Create an order, then make a global invoice and sign it.
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 10)],
                'payments': [(self.bank_pm1, 11600.0)],
                'customer': self.partner_mx,
                'uid': '0001',
            })

        with self.with_mocked_pac_sign_success():
            self.env['l10n_mx_edi.global_invoice.create'] \
                .with_context(order.l10n_mx_edi_action_create_global_invoice()['context'])\
                .create({}) \
                .action_create_global_invoice()

        ginvoice_doc_values = {
            'pos_order_ids': order.ids,
            'state': 'ginvoice_sent',
            'sat_state': 'not_defined',
            'attachment_uuid': order.l10n_mx_edi_cfdi_uuid,
            'attachment_origin': False,
            'cancellation_reason': False,
            'retry_button_needed': False,
            'cancel_button_needed': True,
        }
        self.assertRecordValues(order.l10n_mx_edi_document_ids, [ginvoice_doc_values])
        self.assertRecordValues(order, [{
            'l10n_mx_edi_cfdi_state': 'global_sent',
            'l10n_mx_edi_cfdi_uuid': ginvoice_doc_values['attachment_uuid'],
        }])

        with self.with_pos_session() as _session:
            # Create an invoice triggering the creating of the global refund (failed to be signed).
            with self.with_mocked_pac_sign_error():
                order.action_pos_order_invoice()

            # Sign it.
            invoice = order.account_move
            with self.with_mocked_pac_sign_success():
                self.env['account.move.send'] \
                    .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                    .create({}) \
                    .action_send_and_print()
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        invoice_doc_values = {
            'pos_order_ids': order.ids,
            'state': 'invoice_sent_failed',
            'sat_state': False,
            'attachment_uuid': False,
            'attachment_origin': f'03|{order.l10n_mx_edi_cfdi_uuid}',
            'cancellation_reason': False,
            'retry_button_needed': True,
            'cancel_button_needed': False,
        }
        self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
            invoice_doc_values,
            ginvoice_doc_values,
        ])

        # Retry the global refund.
        with self.with_mocked_pac_sign_success():
            order.l10n_mx_edi_document_ids.sorted()[0].action_retry()
        invoice_doc_values.update({
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
            'attachment_uuid': order.l10n_mx_edi_document_ids.sorted()[0].attachment_uuid,
            'attachment_origin': f"03|{ginvoice_doc_values['attachment_uuid']}",
            'cancellation_reason': False,
            'retry_button_needed': False,
            'cancel_button_needed': True,
        })
        self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
            invoice_doc_values,
            ginvoice_doc_values,
        ])
        self.assertRecordValues(order, [{
            'l10n_mx_edi_cfdi_state': 'global_sent',
            'l10n_mx_edi_cfdi_uuid': ginvoice_doc_values['attachment_uuid'],
        }])
        self._assert_order_cfdi(order, 'test_global_invoiced_order_then_invoiced_then_refund_then_cancel_it')

        # Sat.
        with self.with_mocked_sat_call(lambda _x: 'valid'):
            self.env['l10n_mx_edi.document']._fetch_and_update_sat_status(
                extra_domain=[('id', 'in', order.l10n_mx_edi_document_ids.ids)]
            )
        invoice_doc_values['sat_state'] = 'valid'
        ginvoice_doc_values['sat_state'] = 'valid'
        self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
            invoice_doc_values,
            ginvoice_doc_values,
        ])

        # Try to cancel.
        with self.with_mocked_pac_cancel_error():
            order.l10n_mx_edi_document_ids.sorted()[0].action_cancel()
        invoice_cancel_doc_values = {
            'pos_order_ids': order.ids,
            'state': 'invoice_cancel_failed',
            'sat_state': False,
            'attachment_uuid': invoice_doc_values['attachment_uuid'],
            'attachment_origin': f'03|{order.l10n_mx_edi_cfdi_uuid}',
            'cancellation_reason': '02',
            'retry_button_needed': True,
            'cancel_button_needed': False,
        }
        self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
            invoice_cancel_doc_values,
            invoice_doc_values,
            ginvoice_doc_values,
        ])

        # Retry the cancel.
        with self.with_mocked_pac_cancel_success():
            order.l10n_mx_edi_document_ids.sorted()[0].action_retry()
        invoice_cancel_doc_values.update({
            'state': 'invoice_cancel',
            'sat_state': 'not_defined',
            'attachment_uuid': invoice_doc_values['attachment_uuid'],
            'attachment_origin': f'03|{order.l10n_mx_edi_cfdi_uuid}',
            'cancellation_reason': '02',
            'retry_button_needed': False,
            'cancel_button_needed': False,
        })
        self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
            invoice_cancel_doc_values,
            invoice_doc_values,
            ginvoice_doc_values,
        ])

        # Sat.
        with self.with_mocked_sat_call(lambda _x: 'cancelled'):
            self.env['l10n_mx_edi.document']._fetch_and_update_sat_status(
                extra_domain=[('id', 'in', order.l10n_mx_edi_document_ids.ids)]
            )
        invoice_cancel_doc_values['sat_state'] = 'cancelled'
        self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
            invoice_cancel_doc_values,
            invoice_doc_values,
            ginvoice_doc_values,
        ])
