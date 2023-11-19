# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

from dateutil.relativedelta import relativedelta
from itertools import chain


class AgedPartnerBalanceCustomHandler(models.AbstractModel):
    _name = 'account.aged.partner.balance.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Aged Partner Balance Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if not report.user_has_groups('base.group_multi_currency'):
            options['columns'] = [
                column for column in options['columns']
                if column['expression_label'] not in {'amount_currency', 'currency'}
            ]

        default_order_column = 0
        for index, column in enumerate(options.get('columns')):
            if column.get('expression_label') == 'due_date':
                default_order_column = index + 1
                break
        options['order_column'] = (previous_options or {}).get('order_column') or default_order_column

    def _custom_line_postprocessor(self, report, options, lines):
        partner_lines_map = {}

        # Sort line dicts by partner
        for line in lines:
            model, model_id = report._get_model_info_from_id(line['id'])
            if model == 'res.partner':
                partner_lines_map[model_id] = line

        if partner_lines_map:
            # Query trust for the required partners
            self._cr.execute("""
                SELECT res_id, value_text
                FROM ir_property
                WHERE res_id IN %s
                AND name = 'trust'
                AND company_id IN %s
            """, [
                tuple(f"res.partner,{partner_id}" for partner_id in partner_lines_map),
                tuple(comp['id'] for comp in options.get('multi_company', [])) or (self.env.company.id,),
            ])

            trust_map = {}
            for res_id_str, trust in self._cr.fetchall():
                partner_id = int(res_id_str.split(',')[1])
                trust_map[partner_id] = trust

            # Set the trust key into the line dicts
            for partner_id, line_dict in partner_lines_map.items():
                line_dict['trust'] = trust_map.get(partner_id, 'normal')

        return lines

    def _report_custom_engine_aged_receivable(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        return self._aged_partner_report_custom_engine_common(options, 'asset_receivable', current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_aged_payable(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        return self._aged_partner_report_custom_engine_common(options, 'liability_payable', current_groupby, next_groupby, offset=offset, limit=limit)

    def _aged_partner_report_custom_engine_common(self, options, internal_type, current_groupby, next_groupby, offset=0, limit=None):
        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        def minus_days(date_obj, days):
            return fields.Date.to_string(date_obj - relativedelta(days=days))

        date_to = fields.Date.from_string(options['date']['date_to'])
        periods = [
            (False, fields.Date.to_string(date_to)),
            (minus_days(date_to, 1), minus_days(date_to, 30)),
            (minus_days(date_to, 31), minus_days(date_to, 60)),
            (minus_days(date_to, 61), minus_days(date_to, 90)),
            (minus_days(date_to, 91), minus_days(date_to, 120)),
            (minus_days(date_to, 121), False),
        ]

        def build_result_dict(report, query_res_lines):
            rslt = {f'period{i}': 0 for i in range(len(periods))}

            for query_res in query_res_lines:
                for i in range(len(periods)):
                    period_key = f'period{i}'
                    rslt[period_key] += query_res[period_key]

            if current_groupby == 'id':
                query_res = query_res_lines[0] # We're grouping by id, so there is only 1 element in query_res_lines anyway
                currency = self.env['res.currency'].browse(query_res['currency_id'][0]) if len(query_res['currency_id']) == 1 else None
                rslt.update({
                    'due_date': query_res['due_date'][0] if len(query_res['due_date']) == 1 else None,
                    'amount_currency': report.format_value(query_res['amount_currency'], currency=currency),
                    'currency': currency.display_name if currency else None,
                    'account_name': query_res['account_name'][0] if len(query_res['account_name']) == 1 else None,
                    'expected_date': query_res['expected_date'][0] if len(query_res['expected_date']) == 1 else None,
                    'total': None,
                    'has_sublines': query_res['aml_count'] > 0,
                })
            else:
                rslt.update({
                    'due_date': None,
                    'amount_currency': None,
                    'currency': None,
                    'account_name': None,
                    'expected_date': None,
                    'total': sum(rslt[f'period{i}'] for i in range(len(periods))),
                    'has_sublines': False,
                })

            return rslt

        # Build period table
        period_table_format = ('(VALUES %s)' % ','.join("(%s, %s, %s)" for period in periods))
        params = list(chain.from_iterable(
            (period[0] or None, period[1] or None, i)
            for i, period in enumerate(periods)
        ))
        period_table = self.env.cr.mogrify(period_table_format, params).decode(self.env.cr.connection.encoding)

        # Build query
        tables, where_clause, where_params = report._query_get(options, 'strict_range', domain=[('account_id.account_type', '=', internal_type)])

        currency_table = self.env['res.currency']._get_query_currency_table(options)
        always_present_groupby = "period_table.period_index, currency_table.rate, currency_table.precision"
        if current_groupby:
            select_from_groupby = f"account_move_line.{current_groupby} AS grouping_key,"
            groupby_clause = f"account_move_line.{current_groupby}, {always_present_groupby}"
        else:
            select_from_groupby = ''
            groupby_clause = always_present_groupby
        select_period_query = ','.join(
            f"""
                CASE WHEN period_table.period_index = {i}
                THEN %s * (
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision))
                    - COALESCE(SUM(ROUND(part_debit.amount * currency_table.rate, currency_table.precision)), 0)
                    + COALESCE(SUM(ROUND(part_credit.amount * currency_table.rate, currency_table.precision)), 0)
                )
                ELSE 0 END AS period{i}
            """
            for i in range(len(periods))
        )

        tail_query, tail_params = report._get_engine_query_tail(offset, limit)
        query = f"""
            WITH period_table(date_start, date_stop, period_index) AS ({period_table})

            SELECT
                {select_from_groupby}
                %s * SUM(account_move_line.amount_currency) AS amount_currency,
                ARRAY_AGG(DISTINCT account_move_line.partner_id) AS partner_id,
                ARRAY_AGG(account_move_line.payment_id) AS payment_id,
                ARRAY_AGG(DISTINCT COALESCE(account_move_line.date_maturity, account_move_line.date)) AS report_date,
                ARRAY_AGG(DISTINCT account_move_line.expected_pay_date) AS expected_date,
                ARRAY_AGG(DISTINCT account.code) AS account_name,
                ARRAY_AGG(DISTINCT COALESCE(account_move_line.date_maturity, account_move_line.date)) AS due_date,
                ARRAY_AGG(DISTINCT account_move_line.currency_id) AS currency_id,
                COUNT(account_move_line.id) AS aml_count,
                ARRAY_AGG(account.code) AS account_code,
                {select_period_query}

            FROM {tables}

            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            JOIN account_account account ON account.id = account_move_line.account_id
            JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id

            LEFT JOIN LATERAL (
                SELECT SUM(part.amount) AS amount, part.debit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %s
                GROUP BY part.debit_move_id
            ) part_debit ON part_debit.debit_move_id = account_move_line.id

            LEFT JOIN LATERAL (
                SELECT SUM(part.amount) AS amount, part.credit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %s
                GROUP BY part.credit_move_id
            ) part_credit ON part_credit.credit_move_id = account_move_line.id

            JOIN period_table ON
                (
                    period_table.date_start IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
                )
                AND
                (
                    period_table.date_stop IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
                )

            WHERE {where_clause}

            GROUP BY {groupby_clause}

            HAVING (
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision))
                - COALESCE(SUM(ROUND(part_debit.amount * currency_table.rate, currency_table.precision)), 0)
                + COALESCE(SUM(ROUND(part_credit.amount * currency_table.rate, currency_table.precision)), 0)
            ) != 0
            {tail_query}
        """

        multiplicator = -1 if internal_type == 'liability_payable' else 1
        params = [
            multiplicator,
            *([multiplicator] * len(periods)),
            date_to,
            date_to,
            *where_params,
            *tail_params,
        ]
        self._cr.execute(query, params)
        query_res_lines = self._cr.dictfetchall()

        if not current_groupby:
            return build_result_dict(report, query_res_lines)
        else:
            rslt = []

            all_res_per_grouping_key = {}
            for query_res in query_res_lines:
                grouping_key = query_res['grouping_key']
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                rslt.append((grouping_key, build_result_dict(report, query_res_lines)))

            return rslt

    def open_journal_items(self, options, params):
        params['view_ref'] = 'account.view_move_line_tree_grouped_partner'
        action = self.env['account.report'].open_journal_items(options=options, params=params)
        action.get('context', {}).update({'search_default_group_by_account': 0, 'search_default_group_by_partner': 1})
        return action
