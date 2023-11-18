# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
import json


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def create_from_ui(self, orders, draft=False):
        orders = super().create_from_ui(orders, draft=draft)
        order_ids = self.browse([order['id'] for order in orders])
        for order in order_ids:
            line_to_send = order._get_orderline_to_send()
            if order.state == 'paid' and len(line_to_send['preparation_display_order_line_ids']) > 0:
                self.env['pos_preparation_display.order'].process_order(order.id)

        return orders

    def _update_last_order_changes(self):
        changes = json.loads(self.last_order_preparation_change)
        for line in self.lines:
            if not line.skip_change:
                # This is a strange way of doing things but it is imposed by what was done in the frontend.
                # as this method is a copy of the method updateLastOrderChanges in the frontend.
                note = line.note if hasattr(line, 'note') and line.note else '' # FIXME after oxp
                line_key = f'{line.uuid} - {note}'

                if line_key in changes:
                    changes[line_key]['quantity'] = line.qty
                else:
                    changes[line_key] = {
                        'attribute_value_ids': line.attribute_value_ids.ids,
                        'line_uuid': line.uuid,
                        'product_id': line.product_id.id,
                        'name': line.full_product_name,
                        'note': note,
                        'quantity': line.qty,
                    }

        # Checks whether an orderline has been deleted from the order since it
        # was last sent to the preparation tools. If so we delete it to the changes.
        for line_key in list(changes):
            if not self._get_ordered_line(line_key):
                del changes[line_key]

        self.last_order_preparation_change = json.dumps(changes)

    def _get_ordered_line(self, line_key):
        changes = json.loads(self.last_order_preparation_change)
        if line_key not in changes:
            return True
        for line in self.lines:
            note = line.note if hasattr(line, 'note') and line.note else '' # FIXME after oxp
            if line.uuid == changes[line_key]['line_uuid'] and note == changes[line_key]['note']:
                return True
        return False

    def _get_orderline_to_send(self, cancelled=False):
        order_change = self._changes_to_order(cancelled)
        preparation_display_orderline_ids = []
        for changes_type, changes in order_change.items():
            for change in changes:
                product = self.env['product.product'].browse(change['product_id'])
                if product.pos_categ_ids:
                    quantity = change['quantity']
                    if changes_type == 'cancelled' and change['quantity'] > 0:
                        quantity = -change['quantity']
                    preparation_display_orderline_ids.append({
                        'todo': True,
                        'internal_note': change['note'],
                        'attribute_value_ids': change['attribute_value_ids'] if 'attribute_value_ids' in change else [],
                        'product_id': change['product_id'],
                        'product_quantity': quantity,
                        'product_category_ids': product.pos_categ_ids.ids,
                    })

        return self._prepare_preparation_order(preparation_display_orderline_ids)

    @api.model
    def _prepare_preparation_order(self, orderline):
        return {
            'preparation_display_order_line_ids': orderline,
            'displayed': True,
            'pos_order_id': self.id,
        }

    def _changes_to_order(self, cancelled=False):
        to_add = []
        to_remove = []
        if not cancelled:
            changes = self._get_order_changes()
        else:
            changes = json.loads(self.last_order_preparation_change)
        for line_change in changes.values():
            if line_change['quantity'] > 0 and not cancelled:
                to_add.append(line_change)
            else:
                line_change['quantity'] = abs(line_change['quantity'])
                to_remove.append(line_change)
        return {'new': to_add, 'cancelled': to_remove}

    @api.model
    def is_child_of(self, child, parent):
        if child.parent_id.id:
            if child.parent_id.id == parent:
                return True
            else:
                return self.is_child_of(child.parent_id, parent)
        else:
            return False

    @api.model
    def is_child_of_any(self, child, parents):
        for parent in parents:
            if self.is_child_of(child, parent):
                return True
        return False

    def _get_order_changes(self):
        prepa_category_ids = self._get_order_preparation_categories()
        old_changes = json.loads(self.last_order_preparation_change)
        changes = {}

        # Compares the orderlines of the order with the last ones sent.
        # When one of them has changed, we add the change.
        for orderline in self.lines:
            product = orderline.product_id
            note = orderline.note if hasattr(orderline, 'note') and orderline.note else '' # FIXME after oxp
            line_key = f'{orderline.uuid} - {note}'
            if len(prepa_category_ids) == 0 or set(product.pos_categ_ids.ids).intersection(prepa_category_ids) or self.is_child_of_any(product.pos_categ_ids, prepa_category_ids):
                quantity = orderline.qty
                quantity_diff = quantity - old_changes[line_key]['quantity'] if line_key in old_changes else quantity

                if quantity_diff and not orderline.skip_change:
                    changes[line_key] = {
                        'name': orderline.full_product_name,
                        'product_id': product.id,
                        'attribute_value_ids': orderline.attribute_value_ids.ids,
                        'quantity': quantity_diff,
                        'note': note,
                    }

        # Checks whether an orderline has been deleted from the order since it
        # was last sent to the preparation tools. If so we add this to the changes.

        for line_key, line_resume in old_changes.items():
            if not self.lines.filtered(lambda line: line.uuid == line_resume['line_uuid'] and (line.note if hasattr(line, 'note') and line.note else '') == line_resume['note']):
                line_key = f"{line_resume['line_uuid']} - {line_resume['note']}"
                if not changes.get(line_key):
                    changes[line_key] = {
                        'product_id': line_resume['product_id'],
                        'name': line_resume['name'],
                        'note': line_resume['note'],
                        'attribute_value_ids': line_resume['attribute_value_ids'] if 'attribute_value_ids' in line_resume else [],
                        'quantity': -line_resume['quantity'],
                    }
                else:
                    changes[line_key]['quantity'] -= line_resume['quantity']

        return changes

    def _get_order_preparation_categories(self):
        preparation_display_ids = self.env['pos_preparation_display.display'].search(['|', ('pos_config_ids', '=', self.config_id.id), ('pos_config_ids', '=', False)])
        category_ids = []
        for pdis in preparation_display_ids:
            category_pdis_ids = pdis._get_pos_category_ids().ids
            category_ids.extend(c for c in category_pdis_ids if c not in category_ids)
        return category_ids
