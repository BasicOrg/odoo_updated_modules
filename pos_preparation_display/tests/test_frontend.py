# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_01_preparation_display(self):

        self.main_pos_config.write({
            'iface_tipproduct': True,
            'tip_product_id': self.tip.id,
        })

        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.main_pos_config.id)],
            'category_ids': [(4, self.letter_tray.pos_categ_ids[0].id)],
        })

        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PreparationDisplayTour', login="pos_user")

        order = self.env['pos.order'].search([('amount_paid', '=', 65.89)], limit=1)
        preparation_order = self.env['pos_preparation_display.order'].search([('pos_order_id', '=', order.id)], limit=1)

        self.assertEqual(len(preparation_order.preparation_display_order_line_ids), 1, "The order " + str(order.amount_paid) + " has 1 preparation orderline")
        self.assertEqual(preparation_order.preparation_display_order_line_ids.product_id, self.letter_tray, "The preparation orderline has the product " + self.letter_tray.name)
