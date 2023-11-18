/** @odoo-module */

import { Chatter } from "@mail/core/web/chatter";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    sendWhatsapp() {
        const send = async (threadId) => {
            await new Promise((resolve) => {
                this.env.services.action.doAction(
                    {
                        type: "ir.actions.act_window",
                        name: _t("Send WhatsApp Message"),
                        res_model: "whatsapp.composer",
                        view_mode: "form",
                        views: [[false, "form"]],
                        target: "new",
                        context: {
                            active_model: this.props.threadModel,
                            active_id: threadId,
                        },
                    },
                    { onClose: resolve }
                );
            });
            this.threadService.fetchNewMessages(
                this.threadService.getThread(this.props.threadModel, threadId)
            );
        };
        if (this.props.threadId) {
            send(this.props.threadId);
        } else {
            this.onNextUpdate = (nextProps) => {
                if (nextProps.threadId) {
                    send(nextProps.threadId);
                } else {
                    return true;
                }
            };
            this.props.saveRecord?.();
        }
    },
});
