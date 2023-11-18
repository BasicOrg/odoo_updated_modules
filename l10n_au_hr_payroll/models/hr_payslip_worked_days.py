# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrPayslipWorkedDays(models.Model):
    _inherit = "hr.payslip.worked_days"

    def _compute_amount(self):
        res = super()._compute_amount()
        for wd in self:
            if not wd.payslip_id.contract_id._is_struct_from_country("AU"):
                continue
            # The complete duration of contract not met (Pay for the hours worked)
            if wd.payslip_id.date_from + wd.payslip_id._get_schedule_timedelta() != wd.payslip_id.date_to:
                wage = wd.payslip_id.contract_id.hourly_wage if wd.payslip_id.contract_id else 0
                wd.amount = wage * wd.number_of_hours
            if not wd.payslip_id.edited and wd.is_paid and wd.work_entry_type_id.is_leave \
                    and wd.contract_id.l10n_au_leave_loading == "regular":
                wd.amount *= 1 + (wd.contract_id.l10n_au_leave_loading_rate / 100)
                continue
            rate = 1 + wd.contract_id.l10n_au_casual_loading + wd.work_entry_type_id.l10n_au_penalty_rate
            wd.amount *= rate
        return res
