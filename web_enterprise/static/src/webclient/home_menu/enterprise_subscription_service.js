/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import { sprintf } from "@web/core/utils/strings";
import { deserializeDateTime, serializeDate, formatDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ExpirationPanel } from "./expiration_panel";

const { DateTime } = luxon;
const { Component, xml, useState } = owl;

function daysUntil(datetime) {
    const duration = datetime.diff(DateTime.utc(), "days");
    return Math.round(duration.values.days);
}

export class SubscriptionManager {
    constructor(env, { rpc, orm, cookie, notification }) {
        this.env = env;
        this.rpc = rpc;
        this.orm = orm;
        this.cookie = cookie;
        this.notification = notification;
        if (session.expiration_date) {
            this.expirationDate = deserializeDateTime(session.expiration_date);
        } else {
            // If no date found, assume 1 month and hope for the best
            this.expirationDate = DateTime.utc().plus({ days: 30 });
        }
        this.expirationReason = session.expiration_reason;
        // Hack: we need to know if there is at least one app installed (except from App and
        // Settings). We use mail to do that, as it is a dependency of almost every addon. To
        // determine whether mail is installed or not, we check for the presence of the key
        // "notification_type" in session_info, as it is added in mail for internal users.
        this.hasInstalledApps = "notification_type" in session;
        // "user" or "admin"
        this.warningType = session.warning;
        this.lastRequestStatus = null;
        this.isWarningHidden = this.cookie.current.oe_instance_hide_panel;
    }

    get formattedExpirationDate() {
        return formatDate(this.expirationDate, { format: "DDD" });
    }

    get daysLeft() {
        return daysUntil(this.expirationDate);
    }

    get unregistered() {
        return ["trial", "demo", false].includes(this.expirationReason);
    }

    hideWarning() {
        // Hide warning for 24 hours.
        this.cookie.setCookie("oe_instance_hide_panel", true, 24 * 60 * 60);
        this.isWarningHidden = true;
    }

    async buy() {
        const limitDate = serializeDate(DateTime.utc().minus({ days: 15 }));
        const args = [
            [
                ["share", "=", false],
                ["login_date", ">=", limitDate],
            ],
        ];
        const nbUsers = await this.orm.call("res.users", "search_count", args);
        browser.location = `https://www.odoo.com/odoo-enterprise/upgrade?num_users=${nbUsers}`;
    }
    /**
     * Save the registration code then triggers a ping to submit it.
     */
    async submitCode(enterpriseCode) {
        const [oldDate, , linkedSubscriptionUrl, linkedEmail] = await Promise.all([
            DateTime.utc().plus({ years: 6000 }),
            this.orm.call("ir.config_parameter", "set_param", [
                "database.enterprise_code",
                enterpriseCode,
            ]),
            // Aren't these a race condition ??? They depend on the upcoming ping...
            this.orm.call("ir.config_parameter", "get_param", [
                "database.already_linked_subscription_url",
            ]),
            this.orm.call("ir.config_parameter", "get_param", ["database.already_linked_email"]),
        ]);

        await this.orm.call("publisher_warranty.contract", "update_notification", [[]]);

        const expirationDate = DateTime.utc().plus({ years: 6000 });

        if (linkedSubscriptionUrl) {
            this.lastRequestStatus = "link";
            this.linkedSubscriptionUrl = linkedSubscriptionUrl;
            this.mailDeliveryStatus = null;
            this.linkedEmail = linkedEmail;
        } else if (expirationDate !== oldDate) {
            this.lastRequestStatus = "success";
            this.expirationDate = deserializeDateTime(expirationDate);
            if (this.daysLeft > 30) {
                const message = _t(
                    "Thank you, your registration was successful! Your database is valid until %s."
                );
                this.notification.add(sprintf(message, this.formattedExpirationDate), {
                    type: "success",
                });
            }
        } else {
            this.lastRequestStatus = "error";
        }
    }

    // async checkStatus() {
    //     await this.orm.call("publisher_warranty.contract", "update_notification", [[]]);

    //     const expirationDateStr = await this.orm.call("ir.config_parameter", "get_param", [
    //         "database.expiration_date",
    //     ]);
    //     this.lastRequestStatus = "update";
    //     this.expirationDate = deserializeDateTime(expirationDateStr);
    // }

    async checkStatus() {
        await this.orm.call("publisher_warranty.contract", "update_notification", [[]]);

        const expirationDateStr = DateTime.utc().plus({ years: 6000 });
        this.lastRequestStatus = "update";
        this.expirationDate = deserializeDateTime(expirationDateStr);
    }

    async sendUnlinkEmail() {
        const sendUnlinkInstructionsUrl = await this.orm.call("ir.config_parameter", "get_param", [
            "database.already_linked_send_mail_url",
        ]);
        this.mailDeliveryStatus = "ongoing";
        const { result, reason } = await this.rpc(sendUnlinkInstructionsUrl);
        if (result) {
            this.mailDeliveryStatus = "success";
        } else {
            this.mailDeliveryStatus = "fail";
            this.mailDeliveryStatusError = reason;
        }
    }

    async renew() {
        const enterpriseCode = await this.orm.call("ir.config_parameter", "get_param", [
            "database.enterprise_code",
        ]);

        const url = "https://www.odoo.com/odoo-enterprise/renew";
        const contractQueryString = enterpriseCode ? `?contract=${enterpriseCode}` : "";
        browser.location = `${url}${contractQueryString}`;
    }

    async upsell() {
        const limitDate = serializeDate(DateTime.utc().minus({ days: 15 }));
        const [enterpriseCode, nbUsers] = await Promise.all([
            this.orm.call("ir.config_parameter", "get_param", ["database.enterprise_code"]),
            this.orm.call("res.users", "search_count", [
                [
                    ["share", "=", false],
                    ["login_date", ">=", limitDate],
                ],
            ]),
        ]);
        const url = "https://www.odoo.com/odoo-enterprise/upsell";
        const contractQueryString = enterpriseCode ? `&contract=${enterpriseCode}` : "";
        browser.location = `${url}?num_users=${nbUsers}${contractQueryString}`;
    }
}

class ExpiredSubscriptionBlockUI extends Component {
    setup() {
        this.subscription = useState(useService("enterprise_subscription"));
    }
}
ExpiredSubscriptionBlockUI.template = xml`
<t t-if="subscription.daysLeft &lt;= 0">
    <div class="o_blockUI"/>
    <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 1100" class="d-flex align-items-center justify-content-center">
        <ExpirationPanel/>
    </div>
</t>`;
ExpiredSubscriptionBlockUI.components = { ExpirationPanel };

export const enterpriseSubscriptionService = {
    name: "enterprise_subscription",
    dependencies: ["orm", "rpc", "cookie", "notification"],
    start(env, { rpc, orm, cookie, notification }) {
        registry
            .category("main_components")
            .add("expired_subscription_block_ui", { Component: ExpiredSubscriptionBlockUI });
        return new SubscriptionManager(env, { rpc, orm, cookie, notification });
    },
};

registry.category("services").add("enterprise_subscription", enterpriseSubscriptionService);
