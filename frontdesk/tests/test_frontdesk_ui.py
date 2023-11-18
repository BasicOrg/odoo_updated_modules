# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tests.common import HttpCase

@odoo.tests.tagged('post_install', '-at_install')
class TestFrontDeskURL(HttpCase):
    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------
    def test_frondesk_ui(self):
        '''Testing the UI of the Frontdesk module'''

        station = self.env['frontdesk.frontdesk'].search([('name', '=', 'Office 1')])
        kiosk_values = station.action_open_kiosk()
        access_url = kiosk_values.get('url')

        self.start_tour(access_url, 'quick_check_in_tour', login='admin')
        station.drink_offer = True
        self.start_tour(access_url, 'frontdesk_basic_tour', login='admin')
        station.write({
            'host_selection': True,
            'ask_email': 'required',
        })
        self.start_tour(access_url, 'required_fields_tour', login='admin')
