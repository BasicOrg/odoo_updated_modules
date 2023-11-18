/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class PayrollDashboardActionBox extends Component {
    setup() {
        this.actionService = useService("action");
    }
}

PayrollDashboardActionBox.template = 'hr_payroll.ActionBox';
