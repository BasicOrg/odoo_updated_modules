# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import freezegun

from odoo import http
from odoo.tests import HttpCase, tagged
from odoo.addons.website_sale_renting.tests.common import TestWebsiteSaleRentingCommon

@tagged('-at_install', 'post_install')
class TestUi(HttpCase, TestWebsiteSaleRentingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.computer.type = 'product'
        cls.computer.allow_out_of_stock_order = False
        cls.computer.show_availability = True

        quants = cls.env['stock.quant'].create({
            'product_id': cls.computer.id,
            'inventory_quantity': 5.0,
            'location_id': cls.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quants.action_apply_inventory()

    def test_website_sale_stock_renting_ui(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.start_tour("/web", 'shop_buy_rental_stock_product', login='admin')

    @freezegun.freeze_time('2020-01-01')
    def test_visitor_browse_rental_products(self):
        """
        This tests validate that a visitor can actually browse
        on /shop for rental product with the datepicker and is not met with access error
        because he doesn't read access to warehouse (to check for quantities)
        and the sale.order.lines to check availability of the rental product.
        """
        self.env['product.product'].create({
            'type': 'product',
            'name': 'Test product',
            'rent_ok': True,
            'allow_out_of_stock_order': False,
            'is_published': True,
            'qty_available': 1,
        })
        self.authenticate(None, None)
        response = self.url_open('/shop', {
            'start_date': '2020-01-02 00:00:00',
            'end_date': '2020-01-03 00:00:00',
            'csrf_token': http.Request.csrf_token(self),
        })
        self.assertNotEqual(response.status_code, 403,
                            "An access error was raised, because a public visitor doesn't have access "
                            "to the warehouse and sale order line read access.")
