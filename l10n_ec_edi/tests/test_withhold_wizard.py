# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import TestEcEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEcEdiWithholdWizard(TestEcEdiCommon):

    # ===== TEST METHODS =====

    def test_out_withhold_basic_computes(self):
        wizard, out_invoice = self.get_wizard_and_invoice()
        self.assertFalse(wizard.withhold_line_ids)  # out_withhold has no default withhold lines

        self.env['l10n_ec.wizard.account.withhold.line'].create({
            'invoice_id': out_invoice.id,
            'wizard_id': wizard.id,
            'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').ids[0],
        })
        # creating a withhold line yields the expected values
        self.assertEqual(len(wizard.withhold_line_ids), 1)
        withhold_line = wizard.withhold_line_ids[0]
        self.assertEqual(withhold_line.taxsupport_code, False)
        self.assertEqual(withhold_line.base, 48)
        self.assertEqual(withhold_line.amount, 4.8)

    def test_out_withhold_basic_checks(self):
        wizard, out_invoice = self.get_wizard_and_invoice()

        with self.assertRaises(ValidationError):
            wizard.action_create_and_post_withhold()  # empty withhold can't be posted

        with self.assertRaises(ValidationError):
            self.env['l10n_ec.wizard.account.withhold.line'].create({
                'invoice_id': out_invoice.id,
                'wizard_id': wizard.id,
                'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').ids[0],
                'amount': -10,  # no negative amount in withhold lines
            })

    def test_purchase_invoice_withhold(self, custom_taxpayer=False):
        """Creates a purchase invoice and checks that when adding a withhold
        - the suggested taxes match the product default taxes
        - the tax supports are a subset of the invoice's tax supports
        - the withhold is successfully posted"""

        # Create purchase invoice and withhold wizard
        wizard, purchase_invoice = self.get_wizard_and_purchase_invoice()

        # Validate if the withholding tax established in the product is in the field default line creation wizard
        if not custom_taxpayer:
            wizard_tax_ids = wizard.withhold_line_ids.mapped('tax_id')
            product_invoice_tax_ids = purchase_invoice.invoice_line_ids.mapped('product_id.l10n_ec_withhold_tax_id')
            self.assertTrue(all(p_tax.id in wizard_tax_ids.ids for p_tax in product_invoice_tax_ids))

        # Validation: wizard's tax supports is subset of invoice's tax supports
        wizard_tax_support = set(wizard.withhold_line_ids.mapped('taxsupport_code'))
        invoice_tax_support = set(purchase_invoice._l10n_ec_get_inv_taxsupports_and_amounts().keys())
        self.assertTrue(wizard_tax_support.issubset(invoice_tax_support))

        with freeze_time(self.frozen_today):
            withhold = wizard.action_create_and_post_withhold()
        self.assertEqual(withhold.state, 'posted')

    def test_custom_taxpayer_type_partner_on_purchase_invoice(self):
        """Tests test_purchase_invoice_withhold with a custom taxpayer as a partner."""
        self.set_custom_taxpayer_type_on_partner_a()
        self.test_purchase_invoice_withhold(custom_taxpayer=True)

    def test_withold_invoice_partially_paid(self):
        """
        Tests that a withhold can be created on a partially paid invoice
        """
        wizard, invoice = self.get_wizard_and_invoice({
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_advance_60days').id,
        })
        line_to_reco = invoice.line_ids.filtered(lambda l: l.display_type
                                                 and invoice.currency_id.is_zero(l.balance - invoice.amount_total * 0.3))
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': line_to_reco.balance,
        })._create_payments()

        self.assertEqual(invoice.payment_state, 'partial')

        wizard.withhold_line_ids.create({
            'wizard_id': wizard.id,
            'invoice_id': invoice.id,
            'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').id,
        })

        with freeze_time(self.frozen_today):
            withhold = wizard.action_create_and_post_withhold()

        expected_withhold = self.env['account.move.line'].search([('l10n_ec_withhold_invoice_id', '=', invoice.id)]).mapped('move_id')

        self.assertEqual(withhold, expected_withhold)

    def test_out_withhold_with_two_invoices(self):
        """
        Test that when creating a batch withold for two invoices,
        the withhold lines are well reconciled with their respective
        invoices.
        """

        # Create two customer invoices
        inv_1 = self.get_invoice({'move_type': 'out_invoice', 'partner_id': self.partner_a.id})
        inv_2 = self.get_invoice({'move_type': 'out_invoice', 'partner_id': self.partner_a.id, 'l10n_latam_document_number': '001-001-000000002'})
        (inv_1 + inv_2).action_post()

        # Create the withhold wizard with three withhold lines, to be sure that each line is reconciled with the right invoice
        wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=(inv_1 + inv_2).ids, active_model='account.move').create({
            'withhold_line_ids': [
                Command.create({
                    'invoice_id': inv_1.id,
                    'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').id,
                }),
                Command.create({
                    'invoice_id': inv_1.id,
                    'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_sale_1x100').id,
                }),
                Command.create({
                    'invoice_id': inv_2.id,
                    'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').id,
                })
            ]
        })

        with freeze_time(self.frozen_today):
            withhold = wizard.action_create_and_post_withhold()

        # The two invoices lines should be reconciled with the withhold
        for invoice in (inv_1, inv_2):
            with self.subTest(invoice=invoice):
                self.assertEqual(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').matched_credit_ids.credit_move_id.move_id, withhold)

    # ===== HELPER METHODS =====

    def get_wizard_and_invoice(self, invoice_args=None):
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
        }
        if invoice_args:
            invoice_vals.update(invoice_args)
        invoice = self.get_invoice(invoice_vals)
        invoice.action_post()
        wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=invoice.id, active_model='account.move')
        return wizard.create({}), invoice
