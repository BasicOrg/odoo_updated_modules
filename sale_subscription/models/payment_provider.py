# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentProvider(models.Model):

    _inherit = 'payment.provider'

    @api.model
    def _is_tokenization_required(self, sale_order_id=None, **kwargs):
        """ Override of `payment` to force tokenization when paying for a subscription.

        :param int sale_order_id: The sales order to be paid, as a `sale.order` id.
        :return: Whether tokenization is required.
        :rtype: bool
        """
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id).exists()
            if sale_order.is_subscription or sale_order.subscription_id.is_subscription:
                return True
        return super()._is_tokenization_required(sale_order_id=sale_order_id, **kwargs)
