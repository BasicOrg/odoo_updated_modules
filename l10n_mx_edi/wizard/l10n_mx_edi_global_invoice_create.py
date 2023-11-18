from odoo import _, api, fields, models
from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import GLOBAL_INVOICE_PERIODICITY_DEFAULT_VALUES
from odoo.exceptions import UserError


class L10nMxEdiGlobalInvoiceCreate(models.Model):
    _name = 'l10n_mx_edi.global_invoice.create'
    _description = "Create a global invoice"

    move_ids = fields.Many2many(comodel_name='account.move')

    periodicity = fields.Selection(
        **GLOBAL_INVOICE_PERIODICITY_DEFAULT_VALUES,
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)

        if 'move_ids' in results:
            invoices = self.env['account.move'].browse(results['move_ids'][0][2])

            if any(x.move_type != 'out_invoice' or x.state != 'posted' for x in invoices):
                raise UserError(_("You can only process posted invoices."))
            if len(invoices.company_id) != 1 or len(invoices.journal_id) != 1:
                raise UserError(_("You can only process invoices sharing the same company and journal."))
            if any(not x.l10n_mx_edi_is_cfdi_needed or x.l10n_mx_edi_cfdi_state in ('sent', 'global_sent') for x in invoices):
                raise UserError(_("Some invoices are already sent or not eligible for CFDI."))

        return results

    def action_create_global_invoice(self):
        self.ensure_one()
        self.move_ids._l10n_mx_edi_cfdi_global_invoice_try_send(periodicity=self.periodicity)
