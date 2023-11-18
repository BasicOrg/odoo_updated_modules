# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    def _get_invoice_matching_so_candidates(self, st_line, partner):
        """ Find a match between the bank transaction and some sale orders. If none of them are invoiced, there are
        returned to display a message to the user allowing him to show the matched sale orders.
        If some of them are already matched, the journal items are suggested to the user.

        :param st_line: A statement line.
        :param partner: The partner to consider.
        :return:
            {'allow_auto_reconcile': <bool>, 'amls': <account.move.line>} if some sale orders are invoiced.
            {'sale_orders': <sale.order>} otherwise.
        """
        assert self.rule_type == 'invoice_matching'
        for model in ('sale.order', 'sale.order.line', 'account.move', 'account.move.line'):
            self.env[model].flush_model()

        _numerical_tokens, _exact_tokens, text_tokens = self._get_invoice_matching_st_line_tokens(st_line)
        if not text_tokens:
            return

        sequence_prefix = self.env['ir.sequence'].sudo()\
            .search(
                [('code', '=', 'sale.order'), ('company_id', 'in', (st_line.company_id.id, False))],
                order='company_id',
                limit=1,
            )\
            .prefix
        if not sequence_prefix:
            return

        sequence_prefix = sequence_prefix.lower()
        text_tokens = [x.lower() for x in text_tokens if x.lower().startswith(sequence_prefix)]
        if not text_tokens:
            return

        # Find the sale orders that are not yet invoiced or already invoices.
        domain = [
            ('company_id', '=', st_line.company_id.id),
            '|',
            ('invoice_status', 'in', ('to invoice', 'invoiced')),
            ('state', '=', 'sent'),
        ]
        if self.past_months_limit:
            date_limit = fields.Date.context_today(self) - relativedelta(months=self.past_months_limit)
            domain.append(('date_order', '>=', fields.Date.to_string(date_limit)))

        query = self.env['sale.order']._where_calc(domain)
        tables, where_clause, where_params = query.get_sql()

        additional_conditions = []
        for token in text_tokens:
            additional_conditions.append(r"%s ~ sub.name")
            where_params.append(token)

        self._cr.execute(
            f'''
                WITH sale_order_name AS (
                    SELECT
                        sale_order.id,
                        SUBSTRING(REGEXP_REPLACE(LOWER(sale_order.name), '[^0-9a-z\s]', '', 'g'), '\S(?:.*\S)*') AS name
                    FROM {tables}
                    WHERE {where_clause}
                )
                SELECT sub.id
                FROM sale_order_name sub
                WHERE {' OR '.join(additional_conditions)}
            ''',
            where_params,
        )

        candidate_ids = [r[0] for r in self._cr.fetchall()]
        if candidate_ids:
            sale_orders = self.env['sale.order'].browse(candidate_ids)
            results = {'sale_orders': sale_orders}

            # Find some related invoices.
            aml_domain = self._get_invoice_matching_amls_domain(st_line, partner)
            amls = sale_orders.invoice_ids.line_ids.filtered_domain(aml_domain)
            if amls:
                results['amls'] = amls
                results['allow_auto_reconcile'] = True

            return results

    def _get_invoice_matching_rules_map(self):
        # EXTENDS account
        res = super()._get_invoice_matching_rules_map()
        res[0].append(self._get_invoice_matching_so_candidates)
        return res
