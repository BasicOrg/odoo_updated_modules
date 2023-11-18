/** @odoo-module */

import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu, {
    components: { ...MessagingMenu.components, ThreadIcon },
});
