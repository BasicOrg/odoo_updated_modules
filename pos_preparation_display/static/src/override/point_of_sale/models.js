/** @odoo-module **/
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    // This function send order change to preparation display.
    // For sending changes to printer see printChanges function.
    async sendChanges(cancelled) {
        await this.pos.sendDraftToServer();

        const lastOrderPreparationChange = await this.env.services.orm.call(
            "pos_preparation_display.order",
            "process_order",
            [this.server_id, cancelled]
        );
        if (lastOrderPreparationChange) {
            this.lastOrderPrepaChange = JSON.parse(lastOrderPreparationChange);
        }

        return true;
    },
    setCustomerCount(count) {
        super.setCustomerCount(count);
        this.pos.ordersToUpdateSet.add(this);
    },
});
