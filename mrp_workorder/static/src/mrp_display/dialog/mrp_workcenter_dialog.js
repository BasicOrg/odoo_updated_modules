/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

export class MrpWorkcenterDialog extends ConfirmationDialog {
    static template = "mrp_workorder.MrpWorkcenterDialog";
    static props = {
        ...ConfirmationDialog.props,
        body: { type: String, optional: true },
        workcenters: { type: Array, optional: true },
        disabled: { type: Array, optional: true },
        active: { type: Array, optional: true },
        radioMode: { type: Boolean, default: false, optional: true },
    };

    setup() {
        super.setup();
        this.ormService = useService("orm");
        this.workcenters = [];
        this.state = useState({ activeWorkcenters: this.props.active ? [...this.props.active] : [] });
        for (const workcenter of this.props.workcenters || []) {
            this.workcenters.push({
                id: parseInt(workcenter[0]),
                display_name: workcenter[1],
            });
        }

        onWillStart(async () => {
            if (!this.workcenters.length) {
                await this._loadWorkcenters();
            }
        });
    }

    get active() {
        return this.state.activeWorkcenters.includes(this.workcenter.id);
    }

    get disabled() {
        if (!this.props.disabled) {
            return false;
        }
        return this.props.disabled.includes(this.workcenter.id);
    }

    selectWorkcenter(workcenter) {
        if (this.props.radioMode) {
            this.state.activeWorkcenters = [workcenter.id];
        } else if (this.state.activeWorkcenters.includes(workcenter.id)) {
            this.state.activeWorkcenters = this.state.activeWorkcenters.filter(
                (id) => id !== workcenter.id
            );
        } else {
            this.state.activeWorkcenters.push(workcenter.id);
        }
    }

    confirm() {
        this.props.confirm(
            this.state.activeWorkcenters.map((id) => this.workcenters.find((wc) => wc.id === id))
        );
        this.props.close();
    }

    async _loadWorkcenters() {
        this.workcenters = await this.ormService.searchRead("mrp.workcenter", [], ["display_name"]);
    }
}
