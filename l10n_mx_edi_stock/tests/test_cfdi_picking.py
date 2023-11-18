# -*- coding: utf-8 -*-
from .common import TestMXEdiStockCommon
from odoo import Command
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIPickingXml(TestMXEdiStockCommon):

    def test_delivery_guide(self):
        with freeze_time(self.frozen_today), self.with_mocked_pac_sign_success():
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)
            picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide')

    @freeze_time('2017-01-01')
    def test_delivery_guide_company_branch(self):
        self.env.company.write({
            'child_ids': [Command.create({
                'name': 'Branch A',
                'street': 'Campobasso Norte 3206 - 9000',
                'street2': 'Fraccionamiento Montecarlo',
                'zip': '85134',
                'city': 'Ciudad Obregón',
                'country_id': self.env.ref('base.mx').id,
                'state_id': self.env.ref('base.state_mx_son').id,
            })],
        })
        self.cr.precommit.run()  # load the CoA

        branch = self.env.company.child_ids
        warehouse = self._create_warehouse(company_id=branch.id, partner_id=branch.partner_id.id)
        picking = self._create_picking(warehouse)

        with self.with_mocked_pac_sign_success():
            picking.l10n_mx_edi_cfdi_try_send()
        self._assert_picking_cfdi(picking, 'test_delivery_guide_company_branch')
