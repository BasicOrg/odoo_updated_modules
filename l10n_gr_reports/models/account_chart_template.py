from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gr', 'res.company')
    def _get_gr_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'l10n_gr_69_02',
                'deferred_revenue_account_id': 'l10n_gr_78_02',
            }
        }
