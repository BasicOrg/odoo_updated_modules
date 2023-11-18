# -*- coding: utf-8 -*-
from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_data(self, template_code, company, template_data):
        # Called when installing a Chart of Accounts template in the settings
        super()._post_load_data(template_code, company, template_data)
        company = company or self.env.company
        values = self._get_default_deferred_values(company)
        company.deferred_journal_id = values['deferred_journal']
        company.deferred_expense_account_id = values['deferred_expense_account']
        company.deferred_revenue_account_id = values['deferred_revenue_account']

    @template(model='res.company')
    def _get_account_accountant_res_company(self, template_code):
        # Called when installing the Accountant module
        values = self._get_default_deferred_values(self.env.company)
        return {
            self.env.company.id: {
                'deferred_journal_id': values['deferred_journal'].id,
                'deferred_expense_account_id': values['deferred_expense_account'].id,
                'deferred_revenue_account_id': values['deferred_revenue_account'].id,
            }
        }

    def _get_default_deferred_values(self, company):
        journal = company.deferred_journal_id or self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(company),
            ('type', '=', 'general')
        ], limit=1)
        expense_account = company.deferred_expense_account_id or self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(company),
            ('account_type', '=', 'asset_current')
        ], limit=1)
        revenue_account = company.deferred_revenue_account_id or self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(company),
            ('account_type', '=', 'liability_current')
        ], limit=1)
        return {
            'deferred_journal': journal,
            'deferred_expense_account': expense_account,
            'deferred_revenue_account': revenue_account,
        }
