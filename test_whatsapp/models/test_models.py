# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WhatsAppTestBaseModel(models.Model):
    """ Base test model for whatsapp implementation, with mail thread support
    and number / partner. """
    _description = 'WhatsApp Base Test'
    _name = 'whatsapp.test.base'
    _inherit = [
        'mail.thread',
    ]

    name = fields.Char('Name')
    country_id = fields.Many2one('res.country', 'Country')
    customer_id = fields.Many2one('res.partner', 'Customer')
    phone = fields.Char('Phone', compute='_compute_phone', readonly=False, store=True)
    user_id = fields.Many2one(comodel_name='res.users', string="Salesperson")

    @api.depends('customer_id')
    def _compute_phone(self):
        for record in self.filtered(lambda rec: not rec.phone):
            record.phone = record.customer_id.phone

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']


class WhatsAppTestNoThread(models.Model):
    """ Same as base test model but with no way to get a responsible. """
    _description = 'WhatsApp NoThread / NoResponsible'
    _name = 'whatsapp.test.nothread'

    name = fields.Char('Name')
    country_id = fields.Many2one('res.country', 'Country')
    customer_id = fields.Many2one('res.partner', 'Customer')
    phone = fields.Char('Phone', compute='_compute_phone', readonly=False, store=True)
    user_id = fields.Many2one('res.users', string="Salesperson")

    @api.depends('customer_id')
    def _compute_phone(self):
        for record in self.filtered(lambda rec: not rec.phone):
            record.phone = record.customer_id.phone


class WhatsAppTestResponsible(models.Model):
    """ Same as base test model but with responsible fields """
    _description = 'WhatsApp Responsible Test'
    _name = 'whatsapp.test.responsible'
    _inherit = [
        'whatsapp.test.base',
    ]

    user_ids = fields.Many2many('res.users', string="Salespersons")
