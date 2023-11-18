from odoo import fields, models


class PosPreparationDisplayOrderline(models.Model):
    _name = 'pos_preparation_display.orderline'
    _description = "Point of Sale preparation order line"

    todo = fields.Boolean("Status of the orderline", help="The status of a command line, todo or not")
    internal_note = fields.Char(help="Internal notes written at the time of the order")
    attribute_value_ids = fields.Many2many('product.template.attribute.value', 'pos_pdis_orderline_product_template_attribute_value_rel', string="Selected Attributes")
    product_id = fields.Many2one('product.product', string="Product ID")
    product_quantity = fields.Integer("Quantity of ordered product")
    product_cancelled = fields.Integer("Quantity of cancelled product")
    preparation_display_order_id = fields.Many2one(
        'pos_preparation_display.order', required=True, index=True, ondelete='cascade')

    def change_line_status(self, status):
        orderlines_status = []

        categories = self.mapped('product_id.pos_categ_ids')
        preparation_displays = self.env['pos_preparation_display.display'].search(['|', ('category_ids', 'in', categories.ids), ('category_ids', '=', False)])

        for orderline in self:
            orderline.todo = status[str(orderline.id)]
            orderlines_status.append({
                'id': orderline.id,
                'todo': orderline.todo
            })

        self.env['bus.bus']._sendmany([
            [
                f'preparation_display-{preparation_display.access_token}',
                'change_orderline_status',
                {
                    'preparation_display_id': preparation_display.id,
                    'status': orderlines_status
                }
            ]
            for preparation_display in preparation_displays
        ])

        return True
