# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.appointment.utils import interval_from_events, intervals_overlap
from odoo.addons.resource.models.utils import timezone_datetime


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    partners_on_leave = fields.Many2many('res.partner', string='Partners on leave', compute='_compute_partners_on_leave')

    @api.depends('start', 'stop', 'partner_ids')
    def _compute_partners_on_leave(self):
        self.partners_on_leave = False
        user_events = self.filtered(lambda event: event.appointment_type_id.schedule_based_on == 'users')
        if not user_events:
            return

        calendar_ids = user_events.partner_ids.employee_ids.resource_calendar_id
        calendar_to_employees = user_events.partner_ids.employee_ids.grouped('resource_calendar_id')

        for start, stop, events in interval_from_events(user_events):
            group_calendars = calendar_ids.filtered(lambda calendar: calendar in events.partner_ids.employee_ids.resource_calendar_id)
            calendar_to_unavailabilities = {
                calendar: calendar._unavailable_intervals_batch(
                    timezone_datetime(start), timezone_datetime(stop), calendar_to_employees[calendar].resource_id
                ) for calendar in group_calendars
            }
            for event in events:
                partner_employees = event.partner_ids.employee_ids
                event_partners_on_leave = self.env['res.partner']
                for employee in partner_employees:
                    if not employee.resource_calendar_id or not employee.resource_id:
                        continue
                    unavailabilities = calendar_to_unavailabilities[employee.resource_calendar_id].get(employee.resource_id.id, [])
                    if any(intervals_overlap(unavailability, (event.start, event.stop)) for unavailability in unavailabilities):
                        event_partners_on_leave += employee.user_partner_id
                event.partners_on_leave = event_partners_on_leave

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        # skip if not dealing with appointments
        user_ids = [row['resId'] for row in rows if row.get('resId')]  # remove empty rows
        if not group_bys or group_bys[0] != 'user_id' or not user_ids:
            return super().gantt_unavailability(start_date, end_date, scale, group_bys=group_bys, rows=rows)

        start_datetime = timezone_datetime(fields.Datetime.from_string(start_date))
        end_datetime = timezone_datetime(fields.Datetime.from_string(end_date))

        user_ids = self.env['res.users'].browse(user_ids)
        calendar_ids = user_ids.employee_id.resource_calendar_id
        calendar_to_employee = user_ids.employee_id.grouped('resource_calendar_id')
        calendar_to_unavailabilities = {
            calendar: calendar._unavailable_intervals_batch(
                start_datetime, end_datetime,
                resources=calendar_to_employee[calendar].resource_id
            ) for calendar in calendar_ids}
        for row in rows:
            user_id = user_ids.browse(row.get('resId'))
            if not user_id:
                continue
            user_employee = user_id.employee_id
            user_calendar = user_employee.resource_calendar_id
            if not user_calendar:
                continue
            user_unavailabilities = calendar_to_unavailabilities[user_calendar].get(user_employee.resource_id.id, [])
            row['unavailabilities'] = [{'start': start, 'stop': stop} for start, stop in user_unavailabilities]
        return rows
