# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_br_get_operation_type(self):
        """account.external.tax.mixin override."""
        if self.debit_origin_id:
            return "amountComplementary"
        elif self.move_type == "out_refund":
            return "salesReturn"

        return super()._l10n_br_get_operation_type()

    def _l10n_br_get_invoice_refs(self):
        """account.external.tax.mixin override."""
        origin = self.debit_origin_id or self.reversed_entry_id
        if origin:
            return {
                "invoicesRefs": [
                    {
                        "type": "documentCode",
                        "documentCode": f"account.move_{origin.id}",
                    }
                ]
            }

        return {}
