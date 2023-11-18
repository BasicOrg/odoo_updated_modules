/* @odoo-module */

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Numpad extends Component {
    static props = { extraClass: { type: String, optional: true } };
    static defaultProps = { extraClass: "" };
    static template = "voip.Numpad";

    setup() {
        this.softphone = useState(useService("voip").softphone);
        this.callService = useService("voip.call");
        this.userAgentService = useService("voip.user_agent");
        this.input = useRef("input");
        useEffect(
            (shouldFocus) => {
                if (shouldFocus) {
                    this.input.el.focus();
                    this.softphone.shouldFocus = false;
                }
            },
            () => [this.softphone.shouldFocus]
        );
    }

    /** @param {MouseEvent} ev */
    onClickBackspace(ev) {
        this.softphone.numpad.value = this.softphone.numpad.value.slice(0, -1);
    }

    /** @param {MouseEvent} ev */
    onClickKeypad(ev) {
        const key = ev.target.textContent;
        this.userAgentService.session?.sipSession?.sessionDescriptionHandler.sendDtmf(key);
        this.softphone.numpad.value += key;
        this.input.el.focus();
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        const inputValue = this.softphone.numpad.value.trim();
        if (!inputValue) {
            return;
        }
        this.userAgentService.makeCall({ phone_number: inputValue });
    }
}
