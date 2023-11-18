from odoo import models

class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['extract.mixin', 'account.move']

    def _needs_auto_extract(self):
        # EXTENDS account_invoice_extract
        # If the move is created from an expense, it has been already digitised.
        self.ensure_one()
        if self.expense_sheet_id:
            return False
        return super()._needs_auto_extract()
