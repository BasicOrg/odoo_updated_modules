/* @odoo-module */

import { useExternalListener } from "@odoo/owl";

import { Chatter } from "@mail/core/web/chatter";

import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup(...args) {
        super.setup(...args);
        useExternalListener(this.env.services.voip.bus, "voip-reload-chatter", () =>
            this.load(this.props.resId, ["activities", "attachments", "messages"])
        );
    },
});
