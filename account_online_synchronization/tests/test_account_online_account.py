# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields, tools
from odoo.addons.account_online_synchronization.tests.common import AccountOnlineSynchronizationCommon
from odoo.tests import tagged

_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class TestAccountOnlineAccount(AccountOnlineSynchronizationCommon):

    @freeze_time('2023-08-01')
    def test_get_filtered_transactions(self):
        """ This test verifies that duplicate transactions are filtered """
        self.BankStatementLine.with_context(skip_statement_line_cron_trigger=True).create({
            'date': '2023-08-01',
            'journal_id': self.gold_bank_journal.id,
            'online_transaction_identifier': 'ABCD01',
            'payment_ref': 'transaction_ABCD01',
            'amount': 10.0,
        })

        transactions_to_filtered = [
            self._create_one_online_transaction(transaction_identifier='ABCD01'),
            self._create_one_online_transaction(transaction_identifier='ABCD02'),
        ]

        filtered_transactions = self.account_online_account._get_filtered_transactions(transactions_to_filtered)

        self.assertEqual(
            filtered_transactions,
            [
                {
                    'payment_ref': 'transaction_ABCD02',
                    'date': '2023-08-01',
                    'online_transaction_identifier': 'ABCD02',
                    'amount': 10.0,
                    'partner_name': None,
                }
            ]
        )

    @freeze_time('2023-08-01')
    def test_format_transactions(self):
        transactions_to_format = [
            self._create_one_online_transaction(transaction_identifier='ABCD01'),
            self._create_one_online_transaction(transaction_identifier='ABCD02'),
        ]
        formatted_transactions = self.account_online_account._format_transactions(transactions_to_format)
        self.assertEqual(
            formatted_transactions,
            [
                {
                    'payment_ref': 'transaction_ABCD01',
                    'date': fields.Date.from_string('2023-08-01'),
                    'online_transaction_identifier': 'ABCD01',
                    'amount': 10.0,
                    'online_account_id': self.account_online_account.id,
                    'journal_id': self.gold_bank_journal.id,
                    'partner_name': None,
                },
                {
                    'payment_ref': 'transaction_ABCD02',
                    'date': fields.Date.from_string('2023-08-01'),
                    'online_transaction_identifier': 'ABCD02',
                    'amount': 10.0,
                    'online_account_id': self.account_online_account.id,
                    'journal_id': self.gold_bank_journal.id,
                    'partner_name': None,
                },
            ]
        )

    @freeze_time('2023-08-01')
    def test_format_transactions_invert_sign(self):
        transactions_to_format = [
            self._create_one_online_transaction(transaction_identifier='ABCD01', amount=25.0),
        ]
        self.account_online_account.inverse_transaction_sign = True
        formatted_transactions = self.account_online_account._format_transactions(transactions_to_format)
        self.assertEqual(
            formatted_transactions,
            [
                {
                    'payment_ref': 'transaction_ABCD01',
                    'date': fields.Date.from_string('2023-08-01'),
                    'online_transaction_identifier': 'ABCD01',
                    'amount': -25.0,
                    'online_account_id': self.account_online_account.id,
                    'journal_id': self.gold_bank_journal.id,
                    'partner_name': None,
                },
            ]
        )

    @freeze_time('2023-07-25')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._fetch_odoo_fin')
    def test_retrieve_pending_transactions(self, patched_fetch_odoofin):
        self.account_online_link.state = 'connected'
        patched_fetch_odoofin.side_effect = [{
            'transactions': [
                self._create_one_online_transaction(transaction_identifier='ABCD01', date='2023-07-06'),
                self._create_one_online_transaction(transaction_identifier='ABCD02', date='2023-07-22'),
            ],
            'pendings': [
                self._create_one_online_transaction(transaction_identifier='ABCD03_pending', date='2023-07-25'),
                self._create_one_online_transaction(transaction_identifier='ABCD04_pending', date='2023-07-25'),
            ]
        }]

        start_date = fields.Date.from_string('2023-07-01')
        result = self.account_online_account._retrieve_transactions(date=start_date, include_pendings=True)
        self.assertEqual(
            result,
            {
                'transactions': [
                    {
                        'payment_ref': 'transaction_ABCD01',
                        'date': fields.Date.from_string('2023-07-06'),
                        'online_transaction_identifier': 'ABCD01',
                        'amount': 10.0,
                        'partner_name': None,
                        'online_account_id': self.account_online_account.id,
                        'journal_id': self.gold_bank_journal.id,
                    },
                    {
                        'payment_ref': 'transaction_ABCD02',
                        'date': fields.Date.from_string('2023-07-22'),
                        'online_transaction_identifier': 'ABCD02',
                        'amount': 10.0,
                        'partner_name': None,
                        'online_account_id': self.account_online_account.id,
                        'journal_id': self.gold_bank_journal.id,
                    }
                ],
                'pendings': [
                    {
                        'payment_ref': 'transaction_ABCD03_pending',
                        'date': fields.Date.from_string('2023-07-25'),
                        'online_transaction_identifier': 'ABCD03_pending',
                        'amount': 10.0,
                        'partner_name': None,
                        'online_account_id': self.account_online_account.id,
                        'journal_id': self.gold_bank_journal.id,
                    },
                    {
                        'payment_ref': 'transaction_ABCD04_pending',
                        'date': fields.Date.from_string('2023-07-25'),
                        'online_transaction_identifier': 'ABCD04_pending',
                        'amount': 10.0,
                        'partner_name': None,
                        'online_account_id': self.account_online_account.id,
                        'journal_id': self.gold_bank_journal.id,
                    }
                ]
            }
        )

    @freeze_time('2023-01-01 01:10:15')
    @patch('odoo.addons.base.models.ir_cron.ir_cron._trigger')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._retrieve_transactions', return_value={})
    def test_basic_flow_cron_fetching_transactions(self, patched_transactions, patched_trigger):
        self.addCleanup(self.env.registry.leave_test_mode)
        # flush and clear everything for the new "transaction"
        self.env.invalidate_all()

        self.env.registry.enter_test_mode(self.cr)
        with self.env.registry.cursor() as test_cr:
            test_env = self.env(cr=test_cr)
            test_link_account = self.account_online_link.with_env(test_env)
            test_link_account.state = 'connected'

            # Call fetch_transaction in cron mode and check that a call was made to transaction and that
            # one trigger was created in case import failed due to process being killed.
            test_link_account.with_context(cron=True)._fetch_transactions()
            patched_transactions.assert_called_once()
            cron_limit_time = tools.config['limit_time_real_cron']  # time after which cron process is killed
            limit_time = (cron_limit_time if cron_limit_time > 0 else 300) + 60
            patched_trigger.assert_called_once_with(fields.Datetime.now() + timedelta(seconds=limit_time))
            self.assertEqual(test_link_account.account_online_account_ids[0].fetching_status, 'done')

    @freeze_time('2023-01-01 01:10:15')
    @patch('odoo.addons.base.models.ir_cron.ir_cron._trigger')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._retrieve_transactions', return_value={})
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._refresh', return_value=True)
    def test_basic_flow_manual_fetching_transactions(self, patched_refresh, patched_transactions, patched_trigger):
        # Call fetch_transaction in manual mode and check that a call was made to refresh, nothing to transaction and that
        # one trigger was created immediately to fetch transactions.
        self.account_online_link._fetch_transactions()
        patched_refresh.assert_called_once()
        patched_transactions.assert_not_called()
        patched_trigger.assert_called_once_with(fields.Datetime.now())
        self.assertEqual(self.account_online_account.fetching_status, 'waiting')

    @freeze_time('2023-01-01 01:10:15')
    @patch('odoo.addons.base.models.ir_cron.ir_cron._trigger')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._retrieve_transactions', return_value={})
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._fetch_odoo_fin')
    def test_refresh_incomplete_fetching_transactions(self, patched_refresh, patched_transactions, patched_trigger):
        patched_refresh.return_value = {'success': False}
        # Call fetch_transaction and if call result is false, don't call transaction
        self.account_online_link._fetch_transactions()
        patched_transactions.assert_not_called()
        patched_trigger.assert_not_called()

        patched_refresh.return_value = {'success': False, 'currently_fetching': True}
        # Call fetch_transaction and if call result is false but in the process of fetching, don't call transaction
        # and instead create a cron trigger to check in 3minutes if process has finished
        self.account_online_link._fetch_transactions()
        patched_transactions.assert_not_called()
        patched_trigger.assert_called_once_with(fields.Datetime.now() + timedelta(minutes=3))  # should retry in 3min
        self.assertEqual(self.account_online_account.fetching_status, 'waiting')

    @freeze_time('2023-01-01 01:10:15')
    @patch('odoo.addons.base.models.ir_cron.ir_cron._trigger')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._retrieve_transactions', return_value={})
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._refresh', return_value=True)
    def test_currently_processing_fetching_transactions(self, patched_refresh, patched_transactions, patched_trigger):
        self.account_online_account.fetching_status = 'processing'  # simulate the fact that we are currently creating entries in odoo
        # Call to fetch_transaction should be skipped
        self.account_online_link._fetch_transactions()
        patched_refresh.assert_not_called()
        patched_transactions.assert_not_called()
        patched_trigger.assert_not_called()
