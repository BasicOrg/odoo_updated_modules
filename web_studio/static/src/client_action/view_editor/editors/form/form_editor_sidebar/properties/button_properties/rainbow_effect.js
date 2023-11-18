/** @odoo-module */

import { Component } from "@odoo/owl";
import { FileInput } from "@web/core/file_input/file_input";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";

export class RainbowEffect extends Component {
    static template = "web_studio.ViewEditorSidebar.RainbowEffect";
    static props = {
        effect: { type: true, optional: true },
        onChange: { type: Function },
    };
    static components = {
        FileInput,
        SelectMenu,
        Property,
    };
    setup() {
        this.user = useService("user");
    }
    get choices() {
        return [
            ["fast", _t("Fast")],
            ["medium", _t("Medium")],
            ["slow", _t("Slow")],
            ["no", _t("None")],
        ];
    }
    get rainbowEffect() {
        const effect = this.props.effect;
        if (effect === undefined) {
            return null;
        }
        if (effect === "True") {
            return {};
        }
        return evaluateExpr(effect);
    }
    onRainbowEffectChange(name, value) {
        const effect = this.rainbowEffect;
        if (!value || !value.length) {
            delete effect[name];
        } else {
            effect[name] = value;
        }
        this.props.onChange(effect, "effect");
    }
}
