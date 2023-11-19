from odoo import models
from odoo.http import Stream


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if record._name == 'documents.document' and field_name in ('raw', 'datas', 'db_datas'):
            return Stream.from_attachment(record.attachment_id)

        return super()._record_to_stream(record, field_name)
