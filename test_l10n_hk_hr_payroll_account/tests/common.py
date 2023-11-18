# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10NHkHrPayrollAccountCommon(AccountTestInvoicingCommon):

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        # Hong Kong doesn't have any tax, so this methods will throw errors if we don't return None
        return None

    @classmethod
    def setUpClass(cls, chart_template_ref='hk'):
        super(TestL10NHkHrPayrollAccountCommon, cls).setUpClass(chart_template_ref=chart_template_ref)

        cls.hong_kong_company = cls.env.ref('l10n_hk_hr_payroll.demo_company_hk')

        cls.env.user.company_ids |= cls.hong_kong_company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.hong_kong_company.ids))

        cls.holiday_allocations = cls.env['hr.leave.allocation'].create([{
            'name': 'Paid Time Off %s' % year,
            'holiday_status_id': cls.env.ref('l10n_hk_hr_payroll.holiday_type_hk_annual_leave').id,
            'number_of_days': 20,
            'holiday_type': 'company',
            'mode_company_id': cls.hong_kong_company.id,
            'date_from': date(year, 1, 1),
            'date_to': date(year, 12, 31),
        } for year in range(2021, 2024)])

        cls.resource_calendar = cls.env['resource.calendar'].create({
            'name': 'Test Calendar',
            'company_id': cls.hong_kong_company.id,
            'hours_per_day': 8,
            'tz': "Asia/Hong_Kong",
            'two_weeks_calendar': False,
            'hours_per_week': 40,
            'full_time_required_hours': 40
        })

        cls.resource_calendar_full = cls.resource_calendar.copy({
            'name': 'Calendar (Full)',
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Saturday Morning', 'dayofweek': '5', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
                (0, 0, {'name': 'Saturday Afternoon', 'dayofweek': '5', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
                (0, 0, {'name': 'Sunday Morning', 'dayofweek': '6', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
                (0, 0, {'name': 'Sunday Afternoon', 'dayofweek': '6', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
            ]
        })

        cls.resource_calendar_half = cls.resource_calendar.copy({
            'name': 'Calendar (Half)',
            'hours_per_day': 4,
            'hours_per_week': 20,
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Saturday Morning', 'dayofweek': '5', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
                (0, 0, {'name': 'Sunday Morning', 'dayofweek': '6', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
            ]
        })

        cls.resource_calendar_without_weekend = cls.resource_calendar.copy({
            'name': 'Calendar (Without Weekend)',
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
            ]
        })

        cls.resource_calendar_without_weekend_half = cls.resource_calendar.copy({
            'name': 'Calendar (Without Weekend Half)',
            'hours_per_day': 4,
            'hours_per_week': 20,
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ]
        })

        cls.employee_georges = cls.env['hr.employee'].create({
            'name': 'Georges',
            'private_country_id': cls.env.ref('base.hk').id,
            'resource_calendar_id': cls.resource_calendar_full.id,
            'company_id': cls.hong_kong_company.id,
            'marital': "single",
        })

        cls.contract_georges = cls.env['hr.contract'].create({
            'name': "Georges's contract",
            'employee_id': cls.employee_georges.id,
            'resource_calendar_id': cls.resource_calendar_full.id,
            'company_id': cls.hong_kong_company.id,
            'structure_type_id': cls.env.ref('l10n_hk_hr_payroll.structure_type_employee_cap57').id,
            'date_start': date(2023, 1, 1),
            'wage': 20000.0,
            'hourly_wage': 0.0,
            'l10n_hk_internet': 200.0,
        })

        cls.contract_georges.write({'state': 'open'})

        cls.employee_john = cls.employee_georges.copy({
            'name': 'John Doe',
        })

        cls.contract_john = cls.contract_georges.copy({
            'name': "John's contract",
            'employee_id': cls.employee_john.id,
            'wage': 10000.0,
            'hourly_wage': 0.0,
            'l10n_hk_internet': 200.0,
            'resource_calendar_id': cls.resource_calendar_without_weekend_half.id
        })

        cls.contract_john.write({'state': 'open'})
