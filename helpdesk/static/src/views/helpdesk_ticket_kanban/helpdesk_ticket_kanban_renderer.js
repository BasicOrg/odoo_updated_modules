/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { HelpdeskTicketKanbanHeader } from './helpdesk_ticket_kanban_header';

export class HelpdeskTicketRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: HelpdeskTicketKanbanHeader,
    };
    setup() {
        super.setup();
        this.action = useService('action');
    }

    async deleteGroup(group) {
        if (group && group.groupByField.name === 'stage_id') {
            const action = await group.model.orm.call(
                group.resModel,
                'action_unlink_wizard',
                [group.resId],
                { context: group.context },
            );
            this.action.doAction(action);
            return;
        }
        super.deleteGroup(group);
    }

    canCreateGroup() {
        return super.canCreateGroup() && this.props.list.context.active_model === "helpdesk.team";
    }
}
