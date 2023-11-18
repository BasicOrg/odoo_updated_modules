/** @odoo-module */

import { registry } from "@web/core/registry";

const planningTestTour = registry.category("web_tour.tours").get("planning_test_tour");

registry.category("web_tour.tours").add('sale_planning_test_tour', {
    url: '/web',
    test: true,
    steps: () => [
        ...planningTestTour.steps(), {
            trigger: ".o_gantt_cell.o_gantt_hoverable",
            content: "Click on magnify icon to see list of sale order",
            run: function () {
                this.$anchor[0].dispatchEvent(new PointerEvent("pointermove", { bubbles: true, cancelable: true }));
            },
        }, {
            trigger: ".o_gantt_cells .o_gantt_cell_plan",
            run: 'click',
        }, {
            trigger: "tr.o_data_row td[data-tooltip='Junior Developer']",
            content: "Select the slot and plan orders",
            run: 'click',
        }, {
            trigger: ".o_gantt_pill span:contains(Junior Developer)",
            content: "Check the naming format when SO is selected from magnify icon",
            run: function () {},
        },
    ],
});
