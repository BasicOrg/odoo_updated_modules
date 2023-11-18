# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.tests import tagged

from .common import TestL10NHkHrPayrollAccountCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPayrollHKComputation(TestL10NHkHrPayrollAccountCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='hk'):
        super(TestPayrollHKComputation, cls).setUpClass(chart_template_ref=chart_template_ref)

        cls.georges_payslip = cls.env['hr.payslip'].create({
            'name': 'Georges Payslip',
            'employee_id': cls.employee_georges.id,
            'contract_id': cls.contract_georges.id,
            'struct_id': cls.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id,
            'date_from': date(2023, 1, 1),
            'date_to': date(2023, 1, 31),
        })
        worked_days = cls.georges_payslip.worked_days_line_ids
        worked_days._compute_is_paid()
        worked_days.flush_model(['is_paid'])

    def test_moving_daily_wage(self):
        self.georges_payslip.compute_sheet()
        self.georges_payslip.action_payslip_done()

        self.assertAlmostEqual(self.georges_payslip._get_moving_daily_wage(), 0, delta=0.01, msg="First month payslip doesn't have a moving daily wage")
        self.georges_payslip2 = self.env['hr.payslip'].create({
            'name': 'Georges Payslip',
            'employee_id': self.employee_georges.id,
            'contract_id': self.contract_georges.id,
            'struct_id': self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id,
            'date_from': date(2023, 2, 1),
            'date_to': date(2023, 2, 28),
            'input_line_ids': [(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})],
        })
        self.georges_payslip2.compute_sheet()
        self.georges_payslip2.action_payslip_done()
        # Salary: 20000, Internet Allowance: 200, Actual Working Days: 31
        # Daily Wage: 20200 / 31 = 651.61
        self.assertAlmostEqual(self.georges_payslip2._get_moving_daily_wage(), 651.61, delta=0.01, msg="It should be the daily wage of the first 1 month payslip")

        self.georges_payslip3 = self.env['hr.payslip'].create({
            'name': 'Georges Payslip',
            'employee_id': self.employee_georges.id,
            'contract_id': self.contract_georges.id,
            'struct_id': self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id,
            'date_from': date(2023, 3, 1),
            'date_to': date(2023, 3, 31),
        })
        unpaid_leave = self.env['hr.leave'].create({
            'holiday_type': 'employee',
            'employee_id': self.employee_georges.id,
            'request_date_from': datetime(2023, 3, 7),
            'request_date_to': datetime(2023, 3, 7),
            'holiday_status_id': self.env.ref('l10n_hk_hr_payroll.holiday_type_hk_unpaid_leave').id,
        })
        unpaid_leave.action_validate()
        self.georges_payslip3.compute_sheet()
        self.georges_payslip3.action_payslip_done()
        # First Month:
        # Salary: 20000, Internet Allowance: 200, Actual Working Days: 31
        # Second Month:
        # Salary: 20000, Internet Allowance: 200, Commission: 10000, Actual Working Days: 28
        # Daily Wage: (20000 + 200 + 20000 + 200 + 10000) / (31 + 28) = 854.24
        self.assertAlmostEqual(self.georges_payslip3._get_moving_daily_wage(), 854.24, delta=0.01, msg="Incorrect moving daily wage for the third month payslip")

        self.georges_payslip4 = self.env['hr.payslip'].create({
            'name': 'Georges Payslip',
            'employee_id': self.employee_georges.id,
            'contract_id': self.contract_georges.id,
            'struct_id': self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id,
            'date_from': date(2023, 4, 1),
            'date_to': date(2023, 4, 30),
        })
        self.georges_payslip4.compute_sheet()
        self.georges_payslip4.action_payslip_done()
        # First Month:
        # Salary: 20000, Internet Allowance: 200, Actual Working Days: 31
        # Second Month:
        # Salary: 20000, Internet Allowance: 200, Commission: 10000, Actual Working Days: 28
        # Third Month:
        # Salary: 19354.84, Internet Allowance: 200, Actual Working Days: 30
        # Daily Wage: (20000 + 20000 + 19354.84 + 600 + 10000) / (31 + 28 + 30) = 786.01
        self.assertAlmostEqual(self.georges_payslip4._get_moving_daily_wage(), 786.01, delta=0.01, msg="Incorrect moving daily wage for the fourth month payslip")

    def test_part_time_moving_daily_wage(self):
        self.john_payslip = self.env['hr.payslip'].create({
            'name': 'John Payslip',
            'employee_id': self.employee_john.id,
            'contract_id': self.contract_john.id,
            'struct_id': self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id,
            'date_from': date(2023, 1, 1),
            'date_to': date(2023, 1, 31),
        })
        worked_days = self.john_payslip.worked_days_line_ids
        worked_days._compute_is_paid()
        worked_days.flush_model(['is_paid'])

        self.john_payslip.compute_sheet()
        self.john_payslip.action_payslip_done()

        self.assertAlmostEqual(self.john_payslip._get_moving_daily_wage(), 0, delta=0.01, msg="First month payslip doesn't have a moving daily wage")
        self.john_payslip2 = self.env['hr.payslip'].create({
            'name': 'John Payslip',
            'employee_id': self.employee_john.id,
            'contract_id': self.contract_john.id,
            'struct_id': self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id,
            'date_from': date(2023, 2, 1),
            'date_to': date(2023, 2, 28),
        })
        self.john_payslip2.compute_sheet()
        self.john_payslip2.action_payslip_done()
        # Salary: 10000, Internet Allowance: 200, Actual Working Days: 22
        # Daily Wage: 10200 / 22 = 463.64
        self.assertAlmostEqual(self.john_payslip2._get_moving_daily_wage(), 463.64, delta=0.01, msg="It should be the daily wage of the first 1 month payslip")
