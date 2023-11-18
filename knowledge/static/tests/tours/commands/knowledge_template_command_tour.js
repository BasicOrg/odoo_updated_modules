/** @odoo-module */

import { registry } from "@web/core/registry";
import { endKnowledgeTour, openCommandBar } from '../knowledge_tour_utils.js';
import { stepUtils } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add('knowledge_template_command_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { // go to the custom article
    trigger: '.o_article .o_article_name:contains("EditorCommandsArticle")',
}, { // wait for article to be correctly loaded
    trigger: '.o_breadcrumb_article_name_container:contains("EditorCommandsArticle")',
    run: () => {},
}, { // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openCommandBar(this.$anchor[0]);
    },
}, { // click on the /clipboard command
    trigger: '.oe-powerbox-commandName:contains("Clipboard")',
    run: 'click',
}, { // wait for the block to appear in the editor
    trigger: '.o_knowledge_behavior_type_template',
}, { // enter text into the mail template
    trigger: '.o_knowledge_content > p',
    run: 'text Hello world'
}, { // verify that the text was correctly inserted
    trigger: '.o_knowledge_content > p:contains(Hello world)',
}, { // open the chatter
    trigger: '.btn-chatter',
    run: 'click',
}, {
    trigger: '.o-mail-Thread',
    run: () => {},
}, { // open the follower list of the article
    trigger: '.o-mail-Followers-button',
    run: 'click',
}, { // open the contact record of the follower
    trigger: '.o-mail-Follower-details:contains(HelloWorldPartner)',
    run: 'click',
}, { // verify that the partner form view is fully loaded
    trigger: '.o_breadcrumb .o_last_breadcrumb_item.active:contains(HelloWorldPartner)',
    run: () => {},
}, { // search an article to open it from the contact record
    trigger: 'button[title="Search Knowledge Articles"]',
    run: 'click',
}, { // open the article
    trigger: '.o_command_default:contains(EditorCommandsArticle)',
    run: 'click',
}, { // wait for article to be correctly loaded
    trigger: '.o_breadcrumb_article_name_container:contains("EditorCommandsArticle")',
    run: () => {},
}, { // use the template as description for the contact record
    trigger: '.o_knowledge_behavior_type_template button:contains(Use as)',
    run: 'click',
}, { // check that the content of the template was inserted as description
    trigger: '.o_form_sheet .o_field_html .odoo-editor-editable p:first-child:contains("Hello world")',
    run: () => {},
}, ...endKnowledgeTour()
]});
