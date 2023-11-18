/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { KanbanHeader } from "@web/views/kanban/kanban_header";

export class HelpdeskTicketKanbanHeader extends KanbanHeader {
    /**
     * @override
     */
    _getEmptyGroupLabel(fieldName) {
        if (fieldName === "sla_deadline") {
            return _t("Deadline reached");
        } else {
            return super._getEmptyGroupLabel(fieldName);
        }
    }
}
