# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _start_name = "date_start"
    _stop_name = "date_finished"

    check_ids = fields.One2many('quality.check', 'production_id', string="Checks")

    employee_ids = fields.Many2many('hr.employee', string="working employees", related='workorder_ids.employee_ids')

    def write(self, vals):
        if 'lot_producing_id' in vals:
            self.sudo().workorder_ids.check_ids.filtered(lambda c: c.test_type_id.technical_name == 'register_production').write({'lot_id': vals['lot_producing_id']})
        return super().write(vals)

    def action_add_byproduct(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_workorder.additional.product',
            'views': [[self.env.ref('mrp_workorder.view_mrp_workorder_additional_product_wizard').id, 'form']],
            'name': _('Add By-Product'),
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'default_type': 'byproduct',
            }
        }

    def action_add_component(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_workorder.additional.product',
            'views': [[self.env.ref('mrp_workorder.view_mrp_workorder_additional_product_wizard').id, 'form']],
            'name': _('Add Component'),
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'default_type': 'component',
                'default_company_id': self.company_id.id,
            }
        }

    def action_add_workorder(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_production.additional.workorder',
            'views': [[self.env.ref('mrp_workorder.view_mrp_production_additional_workorder_wizard').id, 'form']],
            'name': _('Add Workorder'),
            'target': 'new',
            'context': {
                'default_production_id': self.id,
            }
        }

    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        productions = super()._split_productions(amounts=amounts, cancel_remaining_qty=cancel_remaining_qty, set_consumed_qty=set_consumed_qty)
        backorders = productions[1:]
        if not backorders:
            return productions
        for wo in backorders.workorder_ids:
            if wo.current_quality_check_id.component_id:
                wo.current_quality_check_id._update_component_quantity()
        return productions

    def pre_button_mark_done(self):
        res = super().pre_button_mark_done()
        for production in self:
            if production.product_tracking in ('lot', 'serial') and not production.lot_producing_id:
                raise UserError(_('You need to supply a Lot/Serial Number for the final product.'))
        self.workorder_ids.verify_quality_checks()
        return res
