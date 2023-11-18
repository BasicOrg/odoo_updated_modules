/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";

export class Category extends Reactive {
    constructor({ id, display_name, color }) {
        super();

        this.id = id;
        this.name = display_name;
        this.color = color;
        this.orderlines = [];
        this.productIds = new Set();
    }
}
