# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import tagged
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


class TestSaleSubscriptionExternalCommon:
    @contextmanager
    def patch_set_external_taxes(self):
        def is_computed_externally(self):
            for move in self.filtered(lambda record: record._name == 'account.move'):
                move.is_tax_computed_externally = move.move_type == 'out_invoice'

            for order in self.filtered(lambda record: record._name == 'sale.order'):
                order.is_tax_computed_externally = True

        # autospec to capture self in call_args_list (https://docs.python.org/3/library/unittest.mock-examples.html#mocking-unbound-methods)
        # patch out the _post because _create_recurring_invoice will auto-post the invoice which will also trigger tax computation, that's not what this test is about
        with patch('odoo.addons.account_external_tax.models.account_move.AccountMove._set_external_taxes', autospec=True) as mocked_set, \
             patch('odoo.addons.account_external_tax.models.account_move.AccountMove._post', lambda self, *args, **kwargs: self), \
             patch('odoo.addons.account_external_tax.models.account_external_tax_mixin.AccountExternalTaxMixin._compute_is_tax_computed_externally', is_computed_externally):
            yield mocked_set


@tagged("-at_install", "post_install")
class TestSaleSubscriptionExternal(TestSubscriptionCommon, TestSaleSubscriptionExternalCommon):
    def test_01_subscription_external_taxes_called(self):
        self.subscription.action_confirm()

        with self.patch_set_external_taxes() as mocked_set:
            invoice = self.subscription.with_context(auto_commit=False)._create_recurring_invoice()

        self.assertIn(
            invoice,
            [args[0] for args, kwargs in mocked_set.call_args_list],
            'Should have queried external taxes on the new invoice.'
        )

    def test_02_subscription_do_payment(self):
        invoice_values = self.subscription._prepare_invoice()
        new_invoice = self.env["account.move"].create(invoice_values)

        payment_method = self.env['payment.token'].create({
            'payment_details': 'Jimmy McNulty',
            'partner_id': self.subscription.partner_id.id,
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'provider_ref': 'Omar Little'
        })

        with self.patch_set_external_taxes() as mocked_set:
            self.subscription._do_payment(payment_method, new_invoice)

        self.assertIn(
            new_invoice,
            [args[0] for args, kwargs in mocked_set.call_args_list],
            'Should have queried external taxes on the new invoice.'
        )
