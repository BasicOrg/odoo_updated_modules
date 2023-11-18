/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/core/web/chatter";
import { useCallbackRecorder } from "@web/webclient/actions/action_hook";

/**
 * Knowledge articles can interact with some records with the help of the
 * @see KnowledgeCommandsService .
 * If any record in a form view has a chatter with the ability to send message
 * and/or attach files, they are a potential target for Knowledge macros.
 */
const ChatterPatch = {
    setup() {
        super.setup(...arguments);
        if (this.env.__knowledgeUpdateCommandsRecordInfo__) {
            useCallbackRecorder(
                this.env.__knowledgeUpdateCommandsRecordInfo__,
                // Callback used to update the values related to the ability to
                // post messages or attach files.
                (recordInfo) => {
                    if (
                        !this.env.model.root?.resId ||
                        recordInfo.resId !== this.env.model.root.resId ||
                        recordInfo.resModel !== this.env.model.root.resModel
                    ) {
                        // Ensure that the current record matches the recordInfo
                        // candidate.
                        return;
                    }
                    // The conditions for the ability to post or attach should
                    // be the same as the ones in the Chatter template.
                    Object.assign(recordInfo, {
                        canPostMessages: this.props.threadId &&
                            this.props.hasMessageList && (
                                this.state.thread?.hasWriteAccess ||
                                (this.state.thread?.hasReadAccess && this.state.thread?.canPostOnReadonly)
                            ),
                        canAttachFiles: this.props.threadId && this.state.thread?.hasWriteAccess
                    });
                }
            );
        }
    }
};

patch(Chatter.prototype, ChatterPatch);
