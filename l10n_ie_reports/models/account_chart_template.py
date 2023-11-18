# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ie', 'res.company')
    def _get_ie_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'l10n_ie_account_2161',
                'deferred_revenue_account_id': 'l10n_ie_account_39',
            }
        }
