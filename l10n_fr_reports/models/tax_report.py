# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools import float_round

class FrenchReportCustomHandler(models.AbstractModel):
    _name = 'l10n_fr.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'French Report Custom Handler'

    def _l10n_fr_get_lines_to_round_closing(self):
        """ Return the xml ids of the tax report lines to be used in the calculation of total difference from
            rounding to be added to the closing entry.
        """
        sales_lines_xml_ids = ['l10n_fr.tax_report_08_taxe', 'l10n_fr.tax_report_09_taxe', 'l10n_fr.tax_report_9B_taxe',
                               'l10n_fr.tax_report_10_taxe', 'l10n_fr.tax_report_11_taxe', 'l10n_fr.tax_report_13_taxe',
                               'l10n_fr.tax_report_14_taxe', 'l10n_fr.tax_report_15']
        purchase_lines_xml_ids = ['l10n_fr.tax_report_19', 'l10n_fr.tax_report_20', 'l10n_fr.tax_report_21']
        return sales_lines_xml_ids, purchase_lines_xml_ids

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # OVERRIDE
        """ Apply the rounding from the French tax report by adding a line to the end of the query results
            representing the sum of the roundings on each line of the tax report.
        """
        report = self.env['account.report'].browse(options['report_id'])
        # Ignore if the rounding accounts cannot be found
        if not company.l10n_fr_rounding_difference_profit_account_id or not company.l10n_fr_rounding_difference_loss_account_id:
            return super()._postprocess_vat_closing_entry_results(company, options, results)

        # Ignore if the French tax groups contain any single group with differing accounts to the rest
        # or any tax group is missing the receivable/payable account (this configuration would be atypical)
        tax_groups = self.env['account.tax.group'].search([
            ('country_id.code', '=', 'FR'),
            ('company_id', '=', company.id),
        ])
        if any(not tax_group.tax_receivable_account_id or not tax_group.tax_payable_account_id for tax_group in tax_groups) or \
           max([len(tax_groups.tax_receivable_account_id), len(tax_groups.tax_payable_account_id), len(tax_groups.advance_tax_payment_account_id)]) > 1:
            return super()._postprocess_vat_closing_entry_results(company, options, results)

        if len(tax_groups.mapped('tax_receivable_account_id')) > 1 \
           or len(tax_groups.mapped('tax_payable_account_id')) > 1 \
           or len(tax_groups.mapped('advance_tax_payment_account_id')) > 1:
            return super()._postprocess_vat_closing_entry_results(company, options, results)

        currency = company.currency_id

        sales_xml_ids, purchase_xml_ids = self._l10n_fr_get_lines_to_round_closing()
        sales_to_round_ids = [self.env.ref(xml_id).id for xml_id in sales_xml_ids]
        purchase_to_round_ids = [self.env.ref(xml_id).id for xml_id in purchase_xml_ids]

        # Get the lines of the report, reinitilize options such that only the column for the closing date is present
        line_data = [line['columns'][0] for line in report._get_lines(options)]

        sales_line_data = filter(lambda x: x['report_line_id'] in sales_to_round_ids, line_data)
        purchase_line_data = filter(lambda x: x['report_line_id'] in purchase_to_round_ids, line_data)

        total_difference = 0
        total_difference += sum([line['no_format'] - float_round(line['no_format'], 0) for line in list(sales_line_data)])
        total_difference -= sum([line['no_format'] - float_round(line['no_format'], 0) for line in list(purchase_line_data)])
        total_difference = currency.round(total_difference)

        if not currency.is_zero(total_difference):
            results.append({
                'tax_name': _('Difference from rounding taxes'),
                'amount': total_difference,
                # The accounts on the tax group ids from the results should be uniform, but we choose the greatest id so that the line appears last on the entry
                'tax_group_id': max([result['tax_group_id'] for result in results]),
                'account_id': company.l10n_fr_rounding_difference_profit_account_id.id if total_difference > 0 else company.l10n_fr_rounding_difference_loss_account_id.id
            })

        return results

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options['buttons'].append({
            'name': _('EDI VAT'),
            'sequence': 30,
            'action': 'send_vat_report',
        })

    def send_vat_report(self, options):
        view_id = self.env.ref('l10n_fr_reports.view_l10n_fr_reports_report_form').id
        return {
            'name': _('EDI VAT'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_fr_reports.send.vat.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {**self.env.context, 'l10n_fr_generation_options': options},
        }
