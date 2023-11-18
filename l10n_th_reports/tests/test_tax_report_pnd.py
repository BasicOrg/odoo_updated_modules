# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nThaiTaxReportTest(AccountSalesReportCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass('th')
        cls.partner_b.write({
            'country_id': cls.env.ref('base.th').id,
            "vat": "12345678",
            "company_registry": "12345678"
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].write({
            'country_id': cls.env.ref('base.th').id,
        })
        return res

    @freeze_time('2023-06-30')
    def test_pnd53_report(self):
        tax_1 = self.env['account.tax'].search([('description', '=', 'Company Withholding Tax 3% (Service)'), ('company_id', '=', self.company_data['company'].id)], limit=1)
        tax_2 = self.env['account.tax'].search([('description', '=', 'Company Withholding Tax 2% (Advertising)'), ('company_id', '=', self.company_data['company'].id)], limit=1)

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_b.id,
            'invoice_date': '2023-05-20',
            'date': '2023-05-20',
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'name': 'product test 1',
                    'price_unit': 1000,
                    'tax_ids': tax_1.ids
                }),
                (0, 0, {
                    'product_id': self.product_b.id,
                    'quantity': 1,
                    'name': 'product test 2',
                    'price_unit': 1000,
                    'tax_ids': tax_2.ids
                })
            ]
        })
        move.action_post()
        self.env.flush_all()

        report = self.env.ref('l10n_th.tax_report_pnd53')
        options = report.get_options()

        report_data = self.env['l10n_th.pnd53.report.handler'].l10n_th_print_pnd_tax_report_pnd53(options)['file_content']
        expected = ("No.,Tax ID,Title,Contact Name,Street,Street2,City,State,Zip,Branch Number,Invoice/Bill Date,Tax Rate,Total Amount,WHT Amount,WHT Condition,Tax Type\n"
                    "1,12345678,บริษัท,Partner B,,,,,,12345678,20/05/2023,3.00,1000.00,30.00,1,Service\n"
                    "2,12345678,บริษัท,Partner B,,,,,,12345678,20/05/2023,2.00,1000.00,20.00,1,Advertising\n").encode()

        self.assertEqual(report_data, expected)

    @freeze_time('2023-06-30')
    def test_pnd3_report(self):
        tax_1 = self.env['account.tax'].search([('description', '=', 'Personal Withholding Tax 1% (Transportation)'), ('company_id', '=', self.company_data['company'].id)], limit=1)
        tax_2 = self.env['account.tax'].search([('description', '=', 'Personal Withholding Tax 2% (Advertising)'), ('company_id', '=', self.company_data['company'].id)], limit=1)

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_b.id,
            'invoice_date': '2023-05-20',
            'date': '2023-05-20',
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'name': 'product test 1',
                    'price_unit': 1000,
                    'tax_ids': tax_1.ids
                }),
                (0, 0, {
                    'product_id': self.product_b.id,
                    'quantity': 1,
                    'name': 'product test 2',
                    'price_unit': 1000,
                    'tax_ids': tax_2.ids
                })
            ]
        })
        move.action_post()
        self.env.flush_all()

        report = self.env.ref('l10n_th.tax_report_pnd3')
        options = report.get_options()

        report_data = self.env['l10n_th.pnd3.report.handler'].l10n_th_print_pnd_tax_report_pnd3(options)['file_content']
        expected = ("No.,Tax ID,Title,Contact Name,Street,Street2,City,State,Zip,Branch Number,Invoice/Bill Date,Tax Rate,Total Amount,WHT Amount,WHT Condition,Tax Type\n"
                    "1,12345678,,Partner B,,,,,,12345678,20/05/2023,1.00,1000.00,10.00,1,Transportation\n"
                    "2,12345678,,Partner B,,,,,,12345678,20/05/2023,2.00,1000.00,20.00,1,Advertising\n").encode()

        self.assertEqual(report_data, expected)
