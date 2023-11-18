/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { Component, onMounted } from "@odoo/owl";


class L10nBeCodaboxSettingsButtons extends Component {
    static props = {
        ...standardWidgetProps,
    };
    static template = "l10n_be_codabox.ActionButtons";

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        onMounted(() => {
            document.querySelector('[name="l10n_be_codabox_fiduciary_vat"]').addEventListener('change', this._onFiduVatChange.bind(this));
        });
    }

    _onFiduVatChange() {
        const vat_input = document.querySelector('[name="l10n_be_codabox_fiduciary_vat"] > input');
        const revoke_button = document.querySelector('[name="l10nBeCodaboxRevokeButton"]');
        if (revoke_button === null) {
            return; // Never connected, button is not rendered
        }
        if (vat_input.value) {
            revoke_button.classList.remove('o_hidden');
        } else {
            revoke_button.classList.add('o_hidden');
        }
    }

    async l10nBeCodaboxConnect() {
        await this._callConfigMethod("l10n_be_codabox_connect", true);
    }

    async l10nBeCodaboxRevoke() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t(
                "This will revoke your access between Codabox and Odoo."
            ),
            confirm: async () => {
                await this._callConfigMethod("l10n_be_codabox_revoke", false);
            },
            cancel: () => { },
        });
    }

    async _callConfigMethod(methodName, save) {
        if (save) {
            await this.env.model.root.save({ reload: false });
        }
        this.env.onClickViewButton({
            clickParams: {
                name: methodName,
                type: "object",
                noSaveDialog: true,
            },
            getResParams: () =>
                pick(this.env.model.root, "context", "evalContext", "resModel", "resId", "resIds"),
        });
    }
}

registry.category("view_widgets").add("l10n_be_codabox_settings_buttons", {
    component: L10nBeCodaboxSettingsButtons,
});
