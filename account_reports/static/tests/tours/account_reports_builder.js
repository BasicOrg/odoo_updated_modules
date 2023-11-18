/** @odoo-module **/

import { Asserts } from "./asserts";
import { registry } from "@web/core/registry";
import { getDifferentParents, stepUtils, triggerPointerEvent } from "@web_tour/tour_service/tour_utils";

function nestedDragAndDrop(source, target) {
    const sourceRect = source.getBoundingClientRect();
    const sourcePosition = {
        clientX: sourceRect.x + sourceRect.width / 2,
        clientY: sourceRect.y + sourceRect.height / 2,
    };

    const targetRect = target.getBoundingClientRect();
    const targetPosition = {
        clientX: targetRect.x + targetRect.width / 2 + 10, // '10' is useNestedSortable() nestInterval value
        clientY: sourcePosition.clientY,
    };

    triggerPointerEvent(source, "pointerdown", true, sourcePosition);
    triggerPointerEvent(source, "pointermove", true, targetPosition);

    for (const parent of getDifferentParents(source, target)) {
        triggerPointerEvent(parent, "pointerenter", false, targetPosition);
    }

    triggerPointerEvent(target, "pointerup", true, targetPosition);
}

function createLine(name) {
    return [
        {
            content: "Click on 'Add new line'",
            trigger: "a:contains('Add a line')",
            run: "click",
        },
        {
            content: "'Create lines' modal is open",
            extra_trigger: ".modal.d-block",
            trigger: ".modal-body .oe_title .o_input",
            run: `text ${ name }`,
        },
        {
            content: "'Save & Close",
            trigger: ".modal-footer .o_form_button_save",
            run: "click",
        },
        {
            content: `'${ name }' exists`,
            trigger: `li span:contains('${ name }')`,
            isCheck: true,
        },
    ];
}

function nestLine(lineIndex) {
    const elementSelector = `li[data-record_index='${ lineIndex }']`;
    const parentSelector = `li[data-record_index='${ parseInt(lineIndex) - 1 }']`;

    return [
        {
            content: `Make ${ elementSelector } children of element above (${ parentSelector })"`,
            trigger: elementSelector,
            run: (actionHelper) => {
                const source = actionHelper.tip_widget.$anchor[0];
                const target = document.querySelector(parentSelector);

                nestedDragAndDrop(source, target)
            }
        },
        {
            content: `Check that ${ elementSelector } is children of element above (${ parentSelector })`,
            trigger: `${ parentSelector } ul ${ elementSelector }`,
            isCheck: true,
        },
    ];
}

registry.category("web_tour.tours").add('account_reports_builder', {
    test: true,
    url: "/web?#action=account_reports.action_account_report_tree",
    steps: () => [
        {
            content: "Open 'Balance Sheet'",
            trigger: "tr > td:nth-child(3):contains('Mister Bigglesworth (ukulele)')",
            run: "click",
        },
        //--------------------------------------------------------------------------------------------------------------
        // Tree
        //--------------------------------------------------------------------------------------------------------------
        {
            content: "Check report structure",
            trigger: ".account_report_lines_list_x2many",
            run: () => {
                // Root
                const root = ".account_report_lines_list_x2many ul";

                // ASSETS
                const assets = `${ root } li[data-record_index='0']`;
                Asserts.DOMContains(assets);

                // Current Assets
                const a_current_assets = `${ assets } ul li[data-record_index='1']`;
                Asserts.DOMContains(a_current_assets);

                // Bank and Cash Accounts
                const a_ca_bank_and_cash_accounts = `${ a_current_assets } ul li[data-record_index='2']`;
                Asserts.DOMContains(a_ca_bank_and_cash_accounts);

                // Receivables
                const a_ca_receivables = `${ a_current_assets } ul li[data-record_index='3']`;
                Asserts.DOMContains(a_ca_receivables);

                // Current Assets
                const a_ca_current_assets = `${ a_current_assets } ul li[data-record_index='4']`;
                Asserts.DOMContains(a_ca_current_assets);

                // Prepayments
                const a_ca_prepayments = `${ a_current_assets } ul li[data-record_index='5']`;
                Asserts.DOMContains(a_ca_prepayments);

                // Plus Fixed Assets
                const a_plus_fixed_assets = `${ assets } ul li[data-record_index='6']`;
                Asserts.DOMContains(a_plus_fixed_assets);

                // Plus Non-current Assets
                const a_plus_non_current_assets = `${ assets } ul li[data-record_index='7']`;
                Asserts.DOMContains(a_plus_non_current_assets);

                // LIABILITIES
                const liabilities = `${ root } li[data-record_index='8']`;
                Asserts.DOMContains(liabilities);

                // Current Liabilities
                const l_current_liabilities = `${ liabilities } ul li[data-record_index='9']`;
                Asserts.DOMContains(l_current_liabilities);

                // Current Liabilities
                const l_cl_liabilities = `${ l_current_liabilities } ul li[data-record_index='10']`;
                Asserts.DOMContains(l_cl_liabilities);

                // Payables
                const l_cl_payables = `${ l_current_liabilities } ul li[data-record_index='11']`;
                Asserts.DOMContains(l_cl_payables);

                // Plus Non-current Liabilities
                const l_plus_non_current_liabilities = `${ liabilities } ul li[data-record_index='12']`;
                Asserts.DOMContains(l_plus_non_current_liabilities);

                // EQUITY
                const equity = `${ root } li[data-record_index='13']`;
                Asserts.DOMContains(equity);

                // Unallocated Earnings
                const e_unallocated_earnings = `${ equity } ul li[data-record_index='14']`;
                Asserts.DOMContains(e_unallocated_earnings);

                // Current Year Unallocated Earnings
                const e_ue_current_year_unallocated_earnings = `${ e_unallocated_earnings } ul li[data-record_index='15']`;
                Asserts.DOMContains(e_ue_current_year_unallocated_earnings);

                // Current Year Earnings
                const e_ue_current_year_earnings = `${ e_ue_current_year_unallocated_earnings } ul li[data-record_index='16']`;
                Asserts.DOMContains(e_ue_current_year_earnings);

                // Current Year Allocated Earnings
                const e_ue_cye_current_year_allocated_earnings = `${ e_ue_current_year_unallocated_earnings } ul li[data-record_index='17']`;
                Asserts.DOMContains(e_ue_cye_current_year_allocated_earnings);

                // Previous Years Unallocated Earnings
                const e_ue_cye_previous_years_unallocated_earnings = `${ e_unallocated_earnings } ul li[data-record_index='18']`;
                Asserts.DOMContains(e_ue_cye_previous_years_unallocated_earnings);

                // Retained Earnings
                const e_retained_earnings = `${ equity } ul li[data-record_index='19']`;
                Asserts.DOMContains(e_retained_earnings);

                // LIABILITIES + EQUITY
                const liabilities_equity = `${ root } li[data-record_index='20']`;
                Asserts.DOMContains(liabilities_equity);

                // OFF BALANCE SHEET ACCOUNTS
                const off_balance_sheet_accounts = `${ root } li[data-record_index='21']`;
                Asserts.DOMContains(off_balance_sheet_accounts);
            },
        },
        //--------------------------------------------------------------------------------------------------------------
        // Create
        //--------------------------------------------------------------------------------------------------------------
        ...createLine('Created Line #1'),
        ...createLine('Created Line #2'),
        ...createLine('Created Line #3'),
        //--------------------------------------------------------------------------------------------------------------
        // Drag and drop
        //--------------------------------------------------------------------------------------------------------------
        {
            content: "Make 'Created Line #1' children of 'OFF BALANCE SHEET ACCOUNTS'",
            trigger: "li[data-record_index='22']",
            run: (actionHelper) => {
                const source = actionHelper.tip_widget.$anchor[0];
                const target = document.querySelector("li[data-record_index='21']");

                nestedDragAndDrop(source, target);
            }
        },
        {
            content: "Close 'Odoo warning' because 'A line with a groupby can not have children'",
            extra_trigger: ".modal.d-block .o_error_dialog",
            trigger: ".modal-header .btn-close",
            run: "click",
        },
        ...nestLine(24),
        ...nestLine(23),
        {
            content: "Move 'Current Assets' above 'ASSETS' making it a root",
            trigger: "li[data-record_index='1']",
            run: (actionHelper) => {
                const source = actionHelper.tip_widget.$anchor[0];
                const target = document.querySelector("li[data-record_index='0']");

                const sourceRect = source.getBoundingClientRect();
                const sourcePosition = {
                    clientX: sourceRect.x + sourceRect.width / 2,
                    clientY: sourceRect.y,
                };

                const targetRect = target.getBoundingClientRect();
                const targetPosition = {
                    clientX: sourcePosition.clientX,
                    clientY: targetRect.y,
                };

                triggerPointerEvent(source, "pointerdown", true, sourcePosition);
                triggerPointerEvent(source, "pointermove", true, targetPosition);

                for (const parent of getDifferentParents(source, target)) {
                    triggerPointerEvent(parent, "pointerenter", false, targetPosition);
                }

                triggerPointerEvent(target, "pointerup", true, targetPosition);
            }
        },
        {
            content: "Click on 'Current Assets'",
            trigger: "li[data-record_index='0'] span:contains('Current Assets')",
            run: "click",
        },
        {
            content: "Close 'Current Assets' edit",
            extra_trigger: ".modal.d-block",
            trigger: ".modal-header .btn-close",
            run: "click",
        },
        //--------------------------------------------------------------------------------------------------------------
        // Edit
        //--------------------------------------------------------------------------------------------------------------
        {
            content: "Open edit of 'Created Line #1'",
            trigger: "li[data-record_index='22'] span:contains('Created Line #1')",
            run: "click",
        },
        {
            content: "Edit 'Created Line #1' to 'Edited Line #1'",
            extra_trigger: ".modal.d-block",
            trigger: ".modal-body .oe_title .o_input",
            run: `text Edited Line #1`,
        },
        {
            content: "'Save & Close",
            trigger: ".modal-footer .o_form_button_save",
            run: "click",
        },
        {
            content: `'Edited Line #1' exists`,
            trigger: `li span:contains('Edited Line #1')`,
            isCheck: true,
        },
        //--------------------------------------------------------------------------------------------------------------
        // Delete
        //--------------------------------------------------------------------------------------------------------------
        {
            content: "Delete 'Created Line #3'",
            trigger: "li[data-record_index='24'] button.trash",
            run: "click",
        },
        {
            content: "Delete 'Edited Line #1'",
            trigger: "li[data-record_index='22'] button.trash",
            run: "click",
        },
        {
            content: "Close 'Confirmation' because 'The line and all his children will be deleted'",
            extra_trigger: ".modal.d-block",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        //--------------------------------------------------------------------------------------------------------------
        // "Reset" form
        //--------------------------------------------------------------------------------------------------------------
        ...stepUtils.saveForm(),
    ],
});
