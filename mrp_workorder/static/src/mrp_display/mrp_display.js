/** @odoo-module */

import { Layout } from "@web/search/layout";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useModel } from "@web/model/model";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { ControlPanelButtons } from "@mrp_workorder/mrp_display/control_panel";
import { MrpDisplayRecord } from "@mrp_workorder/mrp_display/mrp_display_record";
import { MrpWorkcenterDialog } from "./dialog/mrp_workcenter_dialog";
import { makeActiveField } from "@web/model/relational_model/utils";
import { MrpDisplayEmployeesPanel } from "@mrp_workorder/mrp_display/employees_panel";
import { SelectionPopup } from "@mrp_workorder/components/popup";
import { PinPopup } from "@mrp_workorder/components/pin_popup";
import { useConnectedEmployee } from "@mrp_workorder/mrp_display/hooks/employee_hooks";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { Component, onWillDestroy, onWillStart, useState, useSubEnv } from "@odoo/owl";

export class MrpDisplay extends Component {
    static template = "mrp_workorder.MrpDisplay";
    static components = {
        Layout,
        ControlPanelButtons,
        MrpDisplayRecord,
        MrpDisplayEmployeesPanel,
        SelectionPopup,
        PinPopup,
        SearchBar,
    };
    static props = {
        resModel: String,
        action: { type: Object, optional: true },
        comparison: { validate: () => true },
        models: { type: Object },
        domain: { type: Array },
        display: { type: Object, optional: true },
        context: { type: Object, optional: true },
        groupBy: { type: Array, element: String },
        orderBy: { type: Array, element: Object },
    };

    setup() {
        this.homeMenu = useService("home_menu");
        this.viewService = useService("view");
        this.userService = useService("user");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");

        this.display = {
            ...this.props.display,
        };

        this.pickingTypeId = false;
        this.validationStack = {
            "mrp.production": [],
            "mrp.workorder": [],
        };
        if (
            this.props.context.active_model === "stock.picking.type" &&
            this.props.context.active_id
        ) {
            this.pickingTypeId = this.props.context.active_id;
        }
        useSubEnv({
            localStorageName: `mrp_workorder.db_${this.userService.db.name}.user_${this.userService.userId}.picking_type_${this.pickingTypeId}`,
        });

        this.state = useState({
            activeResModel: this.props.context.workcenter_id
                ? "mrp.workorder"
                : this.props.resModel,
            activeWorkcenter: this.props.context.workcenter_id || false,
            workcenters: JSON.parse(localStorage.getItem(this.env.localStorageName)) || [],
        });

        const params = this._makeModelParams();

        this.model = useState(useModel(RelationalModel, params));
        useSubEnv({
            model: this.model,
            reload: async () => {
                await this.model.load();
                await this.useEmployee.getConnectedEmployees();
            },
        });
        this.showEmployeesPanel = JSON.parse(localStorage.getItem("mrp_workorder.show_employees"));
        if (this.showEmployeesPanel === null) {
            this.showEmployeesPanel = false;
            localStorage.setItem(
                "mrp_workorder.show_employees",
                JSON.stringify(this.showEmployeesPanel)
            );
        }
        this.useEmployee = useConnectedEmployee("mrp_display", this.props.context, this.env);
        this.barcode = useService("barcode");
        useBus(this.barcode.bus, "barcode_scanned", (event) =>
            this._onBarcodeScanned(event.detail.barcode)
        );
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.sortOrderCache = { ids: [] };

        onWillStart(async () => {
            this.groups = {
                byproducts: await this.userService.hasGroup("mrp.group_mrp_byproducts"),
                uom: await this.userService.hasGroup("uom.group_uom"),
                workorders: await this.userService.hasGroup("mrp.group_mrp_routings"),
            };
            this.group_mrp_routings = await this.userService.hasGroup("mrp.group_mrp_routings");
            await this.useEmployee.getConnectedEmployees(true);
            if (
                JSON.parse(localStorage.getItem(this.env.localStorageName)) === null &&
                this.group_mrp_routings
            ) {
                this.toggleWorkcenterDialog();
            }
        });
        onWillDestroy(async () => {
            await this.processValidationStack(false);
        });
    }

    addToValidationStack(record, validationCallback) {
        const relevantStack = this.validationStack[record.resModel];
        if (relevantStack.find((rec) => rec.record.resId === record.resId)) {
            return; // Don't add more than once the same record into the stack.
        }
        relevantStack.push({
            record,
            isValidated: false,
            validationCallback,
        });
    }

    close() {
        this.homeMenu.toggle();
    }

    async _onBarcodeScanned(barcode) {
        if (barcode.startsWith("O-BTN.") || barcode.startsWith("O-CMD.")) {
            return;
        }
        const production = this.productions.find((mo) => mo.data.name === barcode);
        if (production) {
            return this._onProductionBarcodeScanned(barcode);
        }
        const workorder = this.relevantRecords.find((wo) => wo.data.barcode === barcode && wo.resModel === 'mrp.workorder');
        if (workorder) {
            return this._onWorkorderBarcodeScanned(workorder);
        }
        const employee = await this.orm.call("mrp.workcenter", "get_employee_barcode", [
            undefined,
            barcode,
        ]);
        if (employee) {
            if (this.useEmployee.popup.SelectionPopup.isShown){
                this.useEmployee.popup.SelectionPopup.close();
            }
            return this.useEmployee.setSessionOwner(employee, undefined);
        }
    }

    async _onProductionBarcodeScanned(barcode){
        const searchItem = Object.values(this.env.searchModel.searchItems).find(
            (i) => i.fieldName === "name"
        );
        const autocompleteValue = {
            label: barcode,
            operator: "=",
            value: barcode,
        }
        this.env.searchModel.addAutoCompletionValues(searchItem.id, autocompleteValue);
    }

    async _onWorkorderBarcodeScanned(workorder){
        const { resModel, resId } = workorder;
        await this.useEmployee.getConnectedEmployees();
        const admin_id = this.useEmployee.employees.admin.id;
        if (admin_id && !workorder.data.employee_ids.records.some((emp) => emp.resId == admin_id)) {
            await this.orm.call(resModel, "button_start", [resId], {
                context: { mrp_display: true },
            });
            this.notification.add(_t("STARTED work on workorder %s", workorder.data.display_name), {
                type: "success",
            });
        } else {
            await this.orm.call(resModel, "stop_employee", [resId, [admin_id]]);
            this.notification.add(_t("STOPPED work on workorder %s", workorder.data.display_name), {
                type: "warning",
            });
        }
        await workorder.load();
        await this.recordUpdated(resId);
        this.render();
        await this.useEmployee.getConnectedEmployees();
    }

    get barcodeTargetRecord(){
        const adminId = this.useEmployee.employees.admin.id;
        const firstWorking = this.relevantRecords.find((r) => r.data.employee_ids.records.some((e) => e.resId === adminId));
        return firstWorking ? firstWorking.resId : this.relevantRecords[0].resId;
    }

    async recordUpdated(wo_id) {
        const MO = this.productions.find((mo) =>
            mo.data.workorder_ids.records.some((wo) => wo.resId === wo_id)
        );
        if (MO) {
            await MO.load();
        }
    }

    get productions() {
        return this.model.root.records;
    }

    get workorders() {
        let workorders = this.model.root.records.map((r) => r.data.workorder_ids.records).flat();
        let state_list = ["ready", "progress", "done"];
        if (this.props.context.show_ready_workorders) {
            state_list = ["ready"];
        } else if (this.props.context.show_progress_workorders) {
            state_list = ["progress"];
        }
        if (!this.props.context.show_all_workorders) {
            workorders = workorders.filter((wo) => state_list.includes(wo.data.state));
        }
        //Should be done in active fields
        const statesComparativeValues = {
            // Smallest value = first. Biggest value = last.
            progress: 0,
            ready: 1,
            pending: 2,
            waiting: 3,
        };
        workorders.sort((wo1, wo2) => {
            const v1 = statesComparativeValues[wo1.data.state];
            const v2 = statesComparativeValues[wo2.data.state];
            const d1 = wo1.data.date_start;
            const d2 = wo2.data.date_start;
            return v1 - v2 || d1 - d2;
        });
        return workorders;
    }

    get workcenters() {
        const workcenters = [];
        for (const workcenter of this.state.workcenters) {
            workcenters.push([workcenter.id, workcenter.display_name]);
        }
        return workcenters;
    }

    toggleWorkcenter(workcenters) {
        const localStorageName = this.env.localStorageName;
        localStorage.setItem(localStorageName, JSON.stringify(workcenters));
        this.state.workcenters = workcenters;
    }

    toggleEmployeesPanel() {
        this.showEmployeesPanel = !this.showEmployeesPanel;
        localStorage.setItem('mrp_workorder.show_employees', JSON.stringify(this.showEmployeesPanel));
        this.render(true);
    }

    filterWorkorderByProduction(workorder, production) {
        return workorder.data.production_id?.[0] === production.resId;
    }

    getproduction(record) {
        if (record.resModel === "mrp.production") {
            return record;
        }
        return this.model.root.records.find((mo) => mo.resId === record.data.production_id[0]);
    }

    getProductionWorkorders(record) {
        if (this.state.activeResModel === "mrp.production") {
            return this.mrp_workorder.root.records.filter((wo) => {
                return this.filterWorkorderByProduction(wo, record);
            });
        }
        return [];
    }

    async processValidationStack(reload=true) {
        const productionIds = [];
        const kwargs = {};
        for (const workorder of this.validationStack["mrp.workorder"]) {
            await workorder.validationCallback();
        }
        for (const production of this.validationStack["mrp.production"]) {
            if (!production.isValidated) {
                productionIds.push(production.record.resId);
                const { data } = production.record;
                if (data.product_tracking == "serial" && !data.show_serial_mass_produce) {
                    kwargs.context = kwargs.context || { skip_redirection: true };
                    if (data.product_qty > 1) {
                        kwargs.context.skip_backorder = true;
                        if (!kwargs.context.mo_ids_to_backorder) {
                            kwargs.context.mo_ids_to_backorder = [];
                        }
                        kwargs.context.mo_ids_to_backorder.push(production.resId);
                    }
                }
            }
        }
        if (productionIds.length) {
            const action = await this.orm.call(
                "mrp.production",
                "button_mark_done",
                productionIds,
                kwargs
            );
            if (action && typeof action === "object") {
                return this.actionService.doAction(action);
            }
            this.validationStack = {
                "mrp.production": [],
                "mrp.workorder": [],
            };
        }
        this.env.reload();
        return { success: true };
    }

    get relevantRecords() {
        if (this.state.activeResModel === "mrp.workorder") {
            if (this.state.activeWorkcenter === -1) {
                // 'My' workcenter selected -> return the ones where the current employee is working on.
                if (this.sortOrderCache.ids.length) {
                    return this.workorders.filter((wo) =>
                        this.sortOrderCache.ids.includes(wo.resId)
                    );
                }
                return this.workorders.filter((wo) => this.adminWorkorderIds.includes(wo.resId));
            }
            return this.workorders.filter(
                (wo) =>
                    wo.data.workcenter_id[0] === this.state.activeWorkcenter &&
                    wo.data.state !== "done"
            );
        }
        return this.model.root.records;
    }

    get relevantSortedRecords() {
        const records = this.relevantRecords;
        if (!this.sortOrderCache.ids.length) {
            this.sortOrderCache.ids = records.map((r) => r.resId);
            return records;
        }
        for (const record of records) {
            if (!this.sortOrderCache.ids.includes(record.resId)){
                this.sortOrderCache.ids.push(record.resId);
            }
        }
        return records.sort(
            (a, b) =>
                this.sortOrderCache.ids.indexOf(a.resId) - this.sortOrderCache.ids.indexOf(b.resId)
        );
    }

    get adminWorkorderIds() {
        const admin_id = this.useEmployee.employees.admin.id;
        const admin = this.useEmployee.employees.connected.find((emp) => emp.id === admin_id);
        const workorderIds = admin ? new Set(admin.workorder.map((wo) => wo.id)) : new Set([]);
        for (const workorder of this.workorders) {
            if (workorder.data.employee_assigned_ids.resIds.includes(admin_id)) {
                workorderIds.add(workorder.resId);
            }
        }
        return [...workorderIds];
    }

    async selectWorkcenter(workcenterId) {
        // Waits all the MO under validation are actually validated before to change the WC.
        const result = await this.processValidationStack();
        if (result.success) {
            this.sortOrderCache.ids = [];
            this.state.activeWorkcenter = Number(workcenterId);
            this.state.activeResModel = this.state.activeWorkcenter
                ? "mrp.workorder"
                : "mrp.production";
        }
    }

    async removeFromValidationStack(record, isValidated=true) {
        const relevantStack = this.validationStack[record.resModel];
        const foundRecord = relevantStack.find(rec => rec.record.resId === record.resId);
        if (isValidated) {
            foundRecord.isValidated = true;
            if (relevantStack.every((rec) => rec.isValidated)) {
                // Empties the validation stack if all under validation MO or WO are validated.
                this.validationStack[record.resModel] = [];
                await this.env.reload();
            }
        } else {
            const index = relevantStack.indexOf(foundRecord);
            relevantStack.splice(index, 1);
        }
    }

    toggleSearchPanel() {
        this.display.searchPanel = !this.display.searchPanel;
        this.render(true);
    }

    toggleWorkcenterDialog() {
        const params = {
            title: _t("Select Work Centers for this station"),
            confirm: this.toggleWorkcenter.bind(this),
            disabled: [],
            active: this.state.workcenters.map((wc) => wc.id),
            radioMode: false,
        };
        this.dialogService.add(MrpWorkcenterDialog, params);
    }

    _makeModelParams() {
        /// Define the structure for related fields
        const { resModel, fields } = this.props.models.find((m) => m.resModel === "mrp.production");
        const activeFields = [];
        for (const fieldName in fields) {
            activeFields[fieldName] = makeActiveField();
        }
        const params = {
            config: { resModel, fields, activeFields },
        };
        const workorderFields = this.props.models.find(
            (m) => m.resModel === "mrp.workorder"
        ).fields;
        params.config.activeFields.workorder_ids.related = {
            fields: workorderFields,
            activeFields: workorderFields,
        };
        const moveFields = this.props.models.find((m) => m.resModel === "stock.move").fields;
        const moveFieldsRelated = {
            fields: moveFields,
            activeFields: moveFields,
        };
        params.config.activeFields.move_raw_ids.related = moveFieldsRelated;
        params.config.activeFields.move_byproduct_ids.related = moveFieldsRelated;
        params.config.activeFields.move_finished_ids.related = moveFieldsRelated;
        const checkFields = this.props.models.find((m) => m.resModel === "quality.check").fields;
        params.config.activeFields.check_ids.related = {
            fields: checkFields,
            activeFields: checkFields,
        };
        params.config.activeFields.workorder_ids.related.activeFields.move_raw_ids.related = {
            fields: moveFields,
            activeFields: moveFields,
        };
        params.config.activeFields.workorder_ids.related.activeFields.check_ids.related = {
            fields: checkFields,
            activeFields: checkFields,
        };
        return params;
    }

    onClickRefresh() {
        this.env.reload();
        this.sortOrderCache.ids = [];
    }

    demoMORecords = [
        {
            id: 1,
            resModel: 'mrp.production',
            data: {
                product_id: [0, "[FURN_8522] Table Top"],
                product_tracking: "serial",
                product_qty: 4,
                product_uom_id: [1, "Units"],
                qty_producing: 4,
                state: "progress",
                move_raw_ids: {
                    records: [
                        {
                            resModel: "stock.move",
                            data: {
                                product_id: [0, "[FURN_7023] Wood Panel"],
                                product_uom_qty: 8,
                                product_uom: [1, "Units"],
                                manual_consumption: true,
                            }
                        }
                    ]
                },
                move_byproduct_ids: {records: []},
                workorder_ids: {
                    records: [
                        {
                            resModel: "mrp.workorder",
                            data: {
                                id: 1,
                                name: "Manual Assembly",
                                workcenter_id: [1, "Assembly Line 1"],
                                check_ids: {
                                    records: []
                                },
                                employee_ids: {records: []}
                            }
                        }
                    ]
                },
                display_name: "WH/MO/00013",
                check_ids: {records: []},
                employee_ids: {records: []}
            },
            fields: {
                state: {
                    selection: [["progress", "In Progress"]],
                    type: "selection"
                },
            },
        },
        {
            id: 2,
            resModel: 'mrp.production',
            data: {
                product_id: [0, "[D_0045_B] Stool (Dark Blue)"],
                product_tracking: "serial",
                product_qty: 1,
                product_uom_id: [1, "Units"],
                qty_producing: 1,
                state: "confirmed",
                move_raw_ids: {records: []},
                move_byproduct_ids: {records: []},
                workorder_ids: {
                    records: [
                        {
                            resModel: "mrp.workorder",
                            data: {
                                id: 1,
                                name: "Assembly  0/6",
                                workcenter_id: [2, "Assembly Line 2"],
                                check_ids: {
                                    records: []
                                },
                                employee_ids: {records: []}
                            }
                        }
                    ]
                },
                display_name: "WH/MO/00015",
                check_ids: {records: []},
                employee_ids: {records: []}
            },
            fields: {
                state: {
                    selection: [["confirmed", "Confirmed"]],
                    type: "selection"
                },
            },
        }
    ]
}
