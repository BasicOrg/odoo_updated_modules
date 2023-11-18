/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { GanttModel } from "@web_gantt/gantt_model";

export class AppointmentBookingGanttModel extends GanttModel {
    /**
     * @override
     */
    load(searchParams) {
        // add some context keys to the search
        return super.load({
            ...searchParams,
            context: { ...searchParams.context, appointment_booking_gantt_show_all_resources: true }
        });
    }
    /**
     * @override
     */
    reschedule(ids, schedule, callback) {
        if (this.metaData.groupedBy && this.metaData.groupedBy[0] === 'partner_ids' && schedule.partner_ids) {
            this.mutex.exec(async () => await this.orm.call(
                this.metaData.resModel,
                "booking_gantt_reschedule_partner_ids",
                [ids, schedule.partner_ids]
            ));
        }
        return super.reschedule(...arguments);
    }

    /**
     * @override
     */
    _getDomain(metaData) {
        const domainList = super._getDomain(metaData);
        const ganttDomain = this.searchParams.context.appointment_booking_gantt_domain;
        if (ganttDomain) {
            return Domain.and([domainList, ganttDomain]).toList();
        }
        return domainList;
    }
}
