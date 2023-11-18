/** @odoo-module **/

import { GanttPopover } from "@web_gantt/gantt_popover";

export class AppointmentBookingGanttPopover extends GanttPopover {
    static template = "appointment.AppointmentBookingGanttPopover";
    static props = [
        ...GanttPopover.props,
        'markAsAttendedCallback',
        'attendedState'
    ];

    onClickAttended() {
        this.props.markAsAttendedCallback();
        this.props.close();
    }
}
