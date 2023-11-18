from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nMxEdiGlobalInvoiceCreate(models.Model):
    _inherit = 'l10n_mx_edi.global_invoice.create'

    pos_order_ids = fields.Many2many(comodel_name='pos.order')

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'l10n_mx_edi'
        results = super().default_get(fields_list)

        if 'pos_order_ids' in results:
            orders = self.env['pos.order'].browse(results['pos_order_ids'][0][2])

            if len(orders.company_id) != 1:
                raise UserError(_("You can only process orders sharing the same company."))
            if any(
                not x.l10n_mx_edi_is_cfdi_needed
                or x.l10n_mx_edi_cfdi_state == 'global_sent'
                or x.account_move
                or x.refunded_order_ids
                for x in orders
            ):
                raise UserError(_("Some orders are already sent or not eligible for CFDI."))

        return results

    def action_create_global_invoice(self):
        # EXTENDS 'l10n_mx_edi'
        self.ensure_one()
        if self.pos_order_ids:
            self.pos_order_ids._l10n_mx_edi_cfdi_global_invoice_try_send(periodicity=self.periodicity)
        else:
            super().action_create_global_invoice()
