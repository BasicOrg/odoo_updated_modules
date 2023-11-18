/** @odoo-module **/

import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

import { TimesheetValidationPivotController } from "./timesheet_validation_pivot_controller";

export const TimesheetValidationPivotView = {
    ...pivotView,
    Controller: TimesheetValidationPivotController,
    buttonTemplate: 'timesheet_grid.TimesheetValidationPivotView.Buttons',
};

registry.category("views").add("timesheet_validation_pivot_view", TimesheetValidationPivotView);
