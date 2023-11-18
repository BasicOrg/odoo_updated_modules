/** @odoo-module */

import {
    click,
    editInput,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent
} from "@web/../tests/helpers/utils";
import { EmbeddedViewBehavior } from "@knowledge/components/behaviors/embedded_view_behavior/embedded_view_behavior";
import { EmbeddedViewManager } from "@knowledge/components/behaviors/embedded_view_behavior/embedded_view_manager";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { HtmlField } from "@web_editor/js/backend/html_field";
import { encodeDataBehaviorProps } from "@knowledge/js/knowledge_utils";

import { onMounted } from "@odoo/owl";

let serverData;
let htmlFieldReadyPromise;
let embedMountedPromise;
/**
 * Insert an embedded kanban view inside a Knowledge article
 * @param {HTMLElement} htmlField - Object HtmlField of Knowledge
 * @param {HTMLElement} target - Target node
 */
const insertKanbanEmbed = async (htmlField, target) => {
    const wysiwyg = htmlField.wysiwyg;
    const behaviorProps = encodeDataBehaviorProps({
        act_window: serverData.actions.actionExternalKanban,
        name: 'External Embed',
        view_type: 'kanban',
        context: {}
    });
    wysiwyg.odooEditor.observerUnactive();
    const embedDiv = document.createElement('div');
    embedDiv.className = "o_knowledge_behavior_anchor o_knowledge_behavior_type_embedded_view";
    embedDiv.setAttribute('data-behavior-props', behaviorProps);
    target.replaceWith(embedDiv);
    await htmlFieldReadyPromise;
    await htmlField.mountBehaviors();
    wysiwyg.odooEditor.observerActive();
    await nextTick();
};

/**
 * This module is testing that the hotkey service works as intended when we have an external embed.
 * This means that when, e.g., when pressing the 'Enter' key inside the embed should have no impact
 * on the article. Pressing 'Enter' inside the article should also not trigger an event inside
 * the embedded view.
 * Testing ensures us that the hotkey service still works as intended inside Knowledge, if not we
 * would need to change its use for embedded views.
 */

QUnit.module("Knowledge External Embeds Hotkeys", (hooks) => {
    hooks.beforeEach(() => {
        htmlFieldReadyPromise = makeDeferred();
        embedMountedPromise = makeDeferred();
        patchWithCleanup(HtmlField.prototype, {
            async startWysiwyg() {
                await super.startWysiwyg(...arguments);
                htmlFieldReadyPromise.resolve(this);
            }
        });
        patchWithCleanup(EmbeddedViewBehavior.prototype, {
            async setup() {
                super.setup(...arguments);
                await this.loadData();
                this.state.waiting = false;
            },
            // Override intersection observer for testing.
            async setupIntersectionObserver() {
                await this.loadData();
                this.state.waiting = false;
            }
        });
        patchWithCleanup(EmbeddedViewManager.prototype, {
            setup() {
                super.setup(...arguments);
                onMounted(() => {
                    embedMountedPromise.resolve();
                });
            },
        });
        serverData = {
            models: {
                knowledge_article: {
                    fields: {
                        display_name: {string: "Displayed name", type: "char"},
                        body: {string: "Body", type: 'html'},
                    },
                    records: [{
                        id: 1,
                        display_name: "My Article",
                        body: `<p class="embedded_view_target"><br/></p>
                            <p class="regular_html_field_node"><br/></p>`
                    }]
                },
                quick_create: {
                    fields: {
                        int: { string: 'Integer', type: 'int', sortable: true },
                        name: { type: 'char', string: "Name given" },
                        state: { type: 'boolean', string: "Done?" }
                    },
                    records: [{
                        id: 1,
                        int: 42,
                        state: true,
                        name: "Answer to life"
                    }, {
                        id: 2,
                        int: 42,
                        state: true,
                        name: "My age"
                    }, {
                        id: 3,
                        int: 69,
                        state: false,
                        name: "Funny number"
                    }]
                }
            },
            actions: {
                actionExternalKanban: {
                    id: 99,
                    xml_id: "action_external_kanban",
                    name: "External Kanban",
                    res_model: "quick_create",
                    type: "ir.actions.act_window",
                    views: [[1, "kanban"]],
                },
            },
            views: {
                "quick_create,1,kanban":
                    `<kanban on_create="quick_create" quick_create="1" default_group_by="state">
                        <field name="int"/>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                <field name="name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
                "quick_create,1,search": "<search></search>"
            },
        };
        setupViewRegistries();
    });
    QUnit.test('Testing normal hotkey behavior: kanban embed', async function (assert) {
        assert.expect(2);
        await makeView({
            type: "form",
            resModel: "knowledge_article",
            serverData,
            arch: `<form js_class="knowledge_article_view_form">
            <sheet>
                <div>
                    <div class="o_knowledge_editor d-flex flex-grow-1">
                        <field name="body" widget="knowledge_article_html_field"/>
                    </div>
                </div>
            </sheet>
        </form>`,
            resId: 1,
            mockRPC(route, { method, model }){
                if (model === "knowledge_article") {
                    switch (method) {
                        case "get_sidebar_articles":
                            return {articles: [], favorite_ids: []};
                    }
                }
            }
        });

        const htmlField = await htmlFieldReadyPromise;

        const editable = htmlField.wysiwyg.odooEditor.editable;
        const embedViewTargetNode = editable.querySelector('.embedded_view_target');
        const regularHtmlFieldNode = editable.querySelector('.regular_html_field_node');

        await insertKanbanEmbed(htmlField, embedViewTargetNode);
        await embedMountedPromise;
        const embedViewWrapperNode = editable.querySelector('.o_knowledge_behavior_anchor.o_knowledge_behavior_type_embedded_view')
        await click(editable, '.o_kanban_group:nth-of-type(1) .o_kanban_quick_add');
        await nextTick();
        // input data that will create a new record via quick_create
        const input = embedViewWrapperNode.querySelector('.o_required_modifier > input');
        await editInput(input, null, "Hello World");
        await triggerEvent(embedViewWrapperNode, null, 'keydown', { key: 'Enter'});
        assert.containsOnce(embedViewWrapperNode, '.o_kanban_record span:contains(Hello World)', "The record should be created");
        // filling the input for a record that will not be created
        await editInput(input, null, "Not created");
        // trigger the focusout to remove the active element from ui service
        await triggerEvent(input, null, 'focusout');
        await nextTick();
        await click(regularHtmlFieldNode, '');
        await nextTick();

        await triggerEvent(regularHtmlFieldNode, null, 'keydown', {key: 'Enter'});
        const value = embedViewWrapperNode.querySelector('.o_kanban_quick_create input').value;
        assert.strictEqual(value, 'Not created', 'The quick_create should not have been triggered');
    });
});
