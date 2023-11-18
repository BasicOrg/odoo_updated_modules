# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class RestaurantPrinter(models.Model):
    _inherit = 'pos.printer'

    device_id = fields.Many2one('iot.device', 'IoT Device', domain="[('type', '=', 'printer')]")
    device_identifier = fields.Char(related="device_id.identifier")
    proxy_ip = fields.Char(size=45, related='device_id.iot_ip', store=True)
