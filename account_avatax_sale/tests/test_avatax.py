from odoo import fields
from odoo.tests.common import tagged
from odoo.tools.misc import formatLang
from odoo.addons.account_avatax.tests.common import TestAccountAvataxCommon
from .mocked_so_response import generate_response


@tagged("-at_install", "post_install")
class TestSaleAvalara(TestAccountAvataxCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        res = super().setUpClass(chart_template_ref)

        # This tax is deliberately wrong with an amount of 1. This is
        # used to make sure we use the tax values that Avatax returns
        # and not the tax values Odoo computes (these values would be
        # wrong if a user manually changes it or if they're partially
        # exempt).
        cls.tax_with_diff_amount = cls.env["account.tax"].create({
            'name': 'CA COUNTY TAX [075] (0.2500 %)',
            'company_id': cls.env.user.company_id.id,
            'amount': 1,
            'amount_type': 'percent',
        })

        cls.sales_user = cls.env['res.users'].create({
            'name': 'Sales user',
            'login': 'sales',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('sales_team.group_sale_salesman').id])],
        })
        cls.env = cls.env(user=cls.sales_user)
        cls.cr = cls.env.cr

        return res

    def assertOrder(self, order, mocked_response=None):
        if mocked_response:
            self.assertRecordValues(order, [{
                'amount_total': 97.68,
                'amount_untaxed': 90.0,
                'amount_tax': 7.68,
            }])
            totals = order.tax_totals
            subtotal_group = totals['groups_by_subtotal']['Untaxed Amount']
            self.assertEqual(len(subtotal_group), 1, 'There should only be one subtotal group (Untaxed Amount)')
            self.assertEqual(subtotal_group[0]['tax_group_amount'], order.amount_tax, 'The tax on tax_totals is different from amount_tax.')
            self.assertEqual(totals['amount_total'], order.amount_total)
            self.assertEqual(totals['formatted_amount_total'], formatLang(self.env, order.amount_total, currency_obj=order.currency_id))

            for avatax_line in mocked_response['lines']:
                so_line = order.order_line.filtered(lambda l: str(l.id) == avatax_line['lineNumber'].split(',')[1])
                self.assertRecordValues(so_line, [{
                    'price_subtotal': avatax_line['taxableAmount'],
                    'price_tax': avatax_line['tax'],
                    'price_total': avatax_line['taxableAmount'] + avatax_line['tax'],
                }])
        else:
            for line in order.order_line:
                product_name = line.product_id.display_name
                self.assertGreater(len(line.tax_id), 0, "Line with %s did not get any taxes set." % product_name)

            self.assertGreater(order.amount_tax, 0.0, "Invoice has a tax_amount of 0.0.")

    def _create_sale_order(self):
        return self.env['sale.order'].create({
            'user_id': self.sales_user.id,
            'partner_id': self.partner.id,
            'fiscal_position_id': self.fp_avatax.id,
            'date_order': '2021-01-01',
            'order_line': [
                (0, 0, {
                    'product_id': self.product_user.id,
                    'tax_id': None,
                    'price_unit': self.product_user.list_price,
                }),
                (0, 0, {
                    'product_id': self.product_user_discound.id,
                    'tax_id': None,
                    'price_unit': self.product_user_discound.list_price,
                }),
                (0, 0, {
                    'product_id': self.product_accounting.id,
                    'tax_id': None,
                    'price_unit': self.product_accounting.list_price,
                }),
                (0, 0, {
                    'product_id': self.product_expenses.id,
                    'tax_id': None,
                    'price_unit': self.product_expenses.list_price,
                }),
                (0, 0, {
                    'product_id': self.product_invoicing.id,
                    'tax_id': None,
                    'price_unit': self.product_invoicing.list_price,
                }),
            ]
        })

    def test_compute_on_send(self):
        order = self._create_sale_order()
        mocked_response = generate_response(order.order_line)
        with self._capture_request(return_value=mocked_response):
            order.action_quotation_send()
        self.assertOrder(order, mocked_response=mocked_response)

    def test_01_odoo_sale_order(self):
        order = self._create_sale_order()
        mocked_response = generate_response(order.order_line)
        with self._capture_request(return_value=mocked_response):
            order.button_update_avatax()
        self.assertOrder(order, mocked_response=mocked_response)

    def test_integration_01_odoo_sale_order(self):
        with self._skip_no_credentials():
            order = self._create_sale_order()
            order.button_update_avatax()
            self.assertOrder(order)


@tagged("-at_install", "post_install")
class TestAccountAvalaraSalesTaxItemsIntegration(TestAccountAvataxCommon):
    """https://developer.avalara.com/certification/avatax/sales-tax-badge/"""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        res = super().setUpClass(chart_template_ref)
        shipping_partner = cls.env["res.partner"].create({
            'name': "Shipping Partner",
            'street': "234 W 18th Ave",
            'city': "Columbus",
            'state_id': cls.env.ref("base.state_us_30").id, # Ohio
            'country_id': cls.env.ref("base.us").id,
            'zip': "43210",
        })

        with cls._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            cls.sale_order = cls.env['sale.order'].create({
                'partner_id': cls.partner.id,
                'partner_shipping_id': shipping_partner.id,
                'fiscal_position_id': cls.fp_avatax.id,
                'date_order': '2021-01-01',
                'order_line': [
                    (0, 0, {
                        'product_id': cls.product.id,
                        'tax_id': None,
                        'price_unit': cls.product.list_price,
                    }),
                ]
            })
            cls.sale_order.button_update_avatax()
        cls.captured_arguments = capture.val
        return res

    def test_item_code(self):
        """Identify customer code (number, ID) to pass to the AvaTax service."""
        line_model, line_id = self.captured_arguments['json']['lines'][0]['number'].split(',')
        self.assertEqual(self.sale_order.order_line, self.env[line_model].browse(int(line_id)))

    def test_item_description(self):
        """Identify item/service/charge description to pass to the AvaTax service with a
        human-readable description or item name.
        """
        line_description = self.captured_arguments['json']['lines'][0]['description']
        self.assertEqual(self.sale_order.order_line.name, line_description)

    def test_tax_code_mapping(self):
        """Association of an item or item group to an AvaTax Tax Code to describe the taxability
        (e.g. Clothing-Shirts – B-to-C).
        """
        tax_code = self.captured_arguments['json']['lines'][0]['taxCode']
        self.assertEqual(self.product.avatax_category_id.code, tax_code)

    def test_doc_code(self):
        """Values that can come across to AvaTax as the DocCode."""
        code = self.captured_arguments['json']['code']
        sent_so = self.env['sale.order'].search([('avatax_unique_code', '=', code)])
        self.assertEqual(self.sale_order, sent_so)

    def test_customer_code(self):
        """Values that can come across to AvaTax as the Customer Code."""
        customer_code = self.captured_arguments['json']['customerCode']
        self.assertEqual(self.sale_order.partner_id.avalara_partner_code, customer_code)

    def test_doc_date(self):
        """Value that comes across to AvaTax as the DocDate."""
        doc_date = self.captured_arguments['json']['date']  # didn't find anything with "DocDate"
        self.assertEqual(self.sale_order.date_order.date(), fields.Date.to_date(doc_date))

    def test_calculation_date(self):
        """Value that is used for Tax Calculation Date in AvaTax."""
        tax_date = self.captured_arguments['json']['taxOverride']['taxDate']
        self.assertEqual(self.sale_order.date_order.date(), fields.Date.to_date(tax_date))

    def test_doc_type(self):
        """DocType used for varying stages of the transaction life cycle."""
        doc_type = self.captured_arguments['json']['type']
        self.assertEqual('SalesOrder', doc_type)

    def test_header_level_destination_address(self):
        """Value that is sent to AvaTax for Destination Address at the header level."""
        destination_address = self.captured_arguments['json']['addresses']['shipTo']
        self.assertEqual(destination_address, {
            'city': 'Columbus',
            'country': 'US',
            'line1': '234 W 18th Ave',
            'postalCode': '43210',
            'region': 'OH',
        })

    def test_header_level_origin_address(self):
        """Value that is sent to AvaTax for Origin Address at the header level."""
        origin_address = self.captured_arguments['json']['addresses']['shipFrom']
        self.assertEqual(origin_address, {
            'city': 'San Francisco',
            'country': 'US',
            'line1': '250 Executive Park Blvd',
            'postalCode': '94134',
            'region': 'CA',
        })

    def test_quantity(self):
        """Value that is sent to AvaTax for the Quantity."""
        quantity = self.captured_arguments['json']['lines'][0]['quantity']
        self.assertEqual(self.sale_order.order_line.product_uom_qty, quantity)

    def test_amount(self):
        """Value that is sent to AvaTax for the Amount."""
        amount = self.captured_arguments['json']['lines'][0]['amount']
        self.assertEqual(self.sale_order.order_line.price_subtotal, amount)

    def test_tax_code(self):
        """Value that is sent to AvaTax for the Tax Code."""
        tax_code = self.captured_arguments['json']['lines'][0]['taxCode']
        self.assertEqual(self.sale_order.order_line.product_id.avatax_category_id.code, tax_code)

    def test_sales_order(self):
        """Ensure that invoices are processed through a logical document lifecycle."""
        self.assertEqual(self.captured_arguments['json']['type'], 'SalesOrder')
        with self._capture_request({'lines': [], 'summary': []}) as capture:
            self.sale_order.action_quotation_send()
            self.sale_order.action_confirm()
            invoice = self.sale_order._create_invoices()
            invoice.button_update_avatax()
        self.assertEqual(capture.val['json']['type'], 'SalesInvoice')

        with self._capture_request({'lines': [], 'summary': []}) as capture:
            invoice.action_post()
        self.assertTrue(capture.val['json']['commit'])

    def test_commit_tax(self):
        """Ensure that invoices are committed/posted for reporting appropriately."""
        with self._capture_request({'lines': [], 'summary': []}) as capture:
            self.sale_order.action_quotation_send()
            self.sale_order.action_confirm()
            invoice = self.sale_order._create_invoices()
            invoice.action_post()
        self.assertTrue(capture.val['json']['commit'])
