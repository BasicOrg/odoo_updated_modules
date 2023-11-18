# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime

from odoo.addons.project_forecast.tests.common import TestCommonForecast


class TestPlanningTimesheet(TestCommonForecast):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.setUpEmployees()
        cls.setUpProjects()

    def test_gantt_progress_bar_group_by_project(self):
        """
        This test ensures that the _gantt_progress_bar_project_id return values is correct.
        - Every project_id present in the res_ids should be present in the dict.
        - The 'value' should be 0 if the project contains no planning slot available in the date range given, else it should be equal to the total of every available slot for the given date range.
        - The 'max value' should be equal to the 'allocated_hours' field for each project.
        """
        projects = project_without_slot, project_slot_not_in_date_range, project_slot_in_date_range = self.env['project.project'].with_context(tracking_disable=True).create([{
            'name': 'Project no slot',
            'allocated_hours': 40,
        }, {
            'name': 'Project slot not in date range',
            'allocated_hours': 50,
        }, {
            'name': 'Project slot in date range',
            'allocated_hours': 60,
        }])
        start_date = datetime(2021, 10, 22, 8, 0, 0)
        end_date = datetime(2021, 10, 29, 8, 0, 0)
        planning_vals = {
            'resource_id': self.resource_joseph.id,
            'state': 'published',
            'allow_timesheets': True,
        }
        self.env["planning.slot"].create([{
            **planning_vals,
            'project_id': project_slot_in_date_range.id,
            'start_datetime': datetime(2021, 10, 25, 8, 0, 0),
            'end_datetime': datetime(2021, 10, 26, 12, 0, 0),
        }, {
            **planning_vals,
            'project_id': project_slot_in_date_range.id,
            'start_datetime': datetime(2021, 10, 26, 13, 0, 0),
            'end_datetime': datetime(2021, 10, 26, 17, 0, 0),
        }, {
            **planning_vals,
            'project_id': project_slot_not_in_date_range.id,
            'start_datetime': datetime(2021, 10, 20, 8, 0, 0),
            'end_datetime': datetime(2021, 10, 21, 12, 0, 0),
        }])
        res_ids = projects.ids
        expected_values = {
            project_without_slot.id: {'value': 0.0, 'max_value': 40.0},
            project_slot_not_in_date_range.id: {'value': 0.0, 'max_value': 50.0},
            project_slot_in_date_range.id: {'value': 16.0, 'max_value': 60.0}, # 12 hours in the 1st slot + 4 hours in the 2nd slot
        }
        values = self.env["planning.slot"]._gantt_progress_bar_project_id(res_ids, start_date, end_date)
        self.assertDictEqual(values, expected_values)
