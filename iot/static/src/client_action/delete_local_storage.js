/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

class MainComponent extends Component {
	setup() {
		let report_list = []
		for (let i = 0; i < browser.localStorage.length; i++)
		{
			if (browser.localStorage.key(i).startsWith("print_report_number_")) {
				const report_id = parseInt(browser.localStorage.key(i).substring("print_report_number_".length));
				if (!isNaN(report_id)) {
					report_list.push(report_id);
				}
			}
		}
		this.orm = useService("orm");
		onWillStart(async () => {
			let report_ids = await this.orm
				.searchRead(
					"ir.actions.report",
					[["id", "in", report_list]],
				)
			this.report_list = report_ids;
		});
	}
	removeFromLocal(id) {
		browser.localStorage.removeItem(`print_report_number_${id}`);
        window.location.reload();
	}
}

MainComponent.template = 'iot.delete_printer';

registry.category("actions").add("iot_delete_linked_devices_action", MainComponent);

export default MainComponent;
