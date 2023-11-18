/** @odoo-module **/

import VariantMixin from '@website_sale/js/sale_variant_mixin';
import { patch } from "@web/core/utils/patch";

/**
 * Update the renting text when the combination change.
 *
 * @param {Event} ev
 * @param {$.Element} $parent
 * @param {object} combination
 */

patch(VariantMixin, {
    _onChangeCombination(ev, $parent, combination) {
        const result = super._onChangeCombination(...arguments);
        if (!this.isWebsite || !combination.is_subscription) {
            return result;
        }

        const $duration = $parent.find(".o_subscription_duration");
        const $unit = $parent.find(".o_subscription_unit");
        $duration.text(combination.subscription_duration > 1 ? combination.subscription_duration : '');
        $unit.text(combination.temporal_unit_display);

        return result;
    }
});
