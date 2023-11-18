# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class CustomerStatementReport(models.AbstractModel):
    _name = 'report.l10n_account_customer_statements.customer_statements'
    _description = "Customer Statements Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env['res.partner'].browse(data['context']['active_ids'])
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': 'res.partner',
            'docs': docs,
            'company': self.env.company,
            **data,
        }
