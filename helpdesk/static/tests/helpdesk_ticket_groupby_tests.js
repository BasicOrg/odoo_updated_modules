/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { start } from "@mail/../tests/helpers/test_utils";
import { checkLabels, checkLegend, selectMode } from "@web/../tests/views/graph_view_tests";

let target;
let serverData;

QUnit.module("helpdesk", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv.mockServer.models['helpdesk.ticket'] = {
            fields: {
                id: { string: "Id", type: "integer" },
                name: { string: "Name", type: "char" },
                sla_deadline: {
                    string: "SLA Deadline",
                    type: "date",
                    store: true,
                    sortable: true,
                },
            },
            records: [{ id: 1, name: "My ticket", sla_deadline: false }],
        };
        serverData = {
            views: {
                "helpdesk.ticket,false,graph": `<graph/>`,
                "helpdesk.ticket,false,search": `<search/>`,
            },
        }
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("helpdesk_ticket_list");

    QUnit.test("Test group label for empty SLA Deadline in tree", async function (assert) {
        const views = {
            "helpdesk.ticket,false,list":
                `<tree js_class="helpdesk_ticket_list">
                    <field name="sla_deadline" widget="remaining_days"/>
                </tree>`,
            "helpdesk.ticket,false,search": `<search/>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "helpdesk.ticket",
            views: [[false, "tree"]],
            context: { group_by: ["sla_deadline"] },
        });

        assert.strictEqual(target.querySelector(".o_group_name").innerText, "Deadline reached (1)");
    });

    QUnit.module("helpdesk_ticket_kanban");

    QUnit.test("Test group label for empty SLA Deadline in kanban", async function (assert) {
        const views = {
            "helpdesk.ticket,false,kanban":
                `<kanban js_class="helpdesk_ticket_kanban" default_group_by="sla_deadline">
                    <templates>
                        <t t-name="kanban-box"/>
                    </templates>
                </kanban>`,
            "helpdesk.ticket,false,search": `<search/>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "helpdesk.ticket",
            views: [[false, "kanban"]],
        });

        assert.strictEqual(target.querySelector(".o_column_title").innerText, "Deadline reached");
    });

    QUnit.module("helpdesk_ticket_pivot");

    QUnit.test("Test group label for empty SLA Deadline in pivot", async function (assert) {
        const views = {
            "helpdesk.ticket,false,pivot":
                `<pivot js_class="helpdesk_ticket_pivot">
                    <field name="sla_deadline" type="row"/>
                </pivot>`,
            "helpdesk.ticket,false,search": `<search/>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "helpdesk.ticket",
            views: [[false, "pivot"]],
        });

        assert.strictEqual(
            target.querySelector("tr:nth-of-type(2) .o_pivot_header_cell_closed").innerText,
            "Deadline reached",
        );
    });

    QUnit.module("helpdesk_ticket_graph");

    QUnit.test("Test group label for empty SLA Deadline in graph", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "helpdesk.ticket",
            groupBy: ["sla_deadline"],
            arch: `
                <graph js_class="helpdesk_ticket_graph">
                    <field name="sla_deadline"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="group_by_sla_deadline" string="SLA Deadline" context="{ 'group_by': 'sla_deadline:day' }"/>
                </search>
            `,
        });
        checkLabels(assert, graph, ["Deadline reached"]);
        checkLegend(assert, graph, ["Count"]);

        await selectMode(target, "pie");

        checkLabels(assert, graph, ["Deadline reached"]);
        checkLegend(assert, graph, ["Deadline reached"]);
    });
});
