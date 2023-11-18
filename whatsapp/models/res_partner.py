# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

from odoo.addons.phone_validation.tools import phone_validation


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _find_or_create_from_number(self, number, name=False):
        """ Number should come currently from whatsapp and contain country info. """
        number_with_sign = '+' + number
        format_number = phone_validation.phone_format(number_with_sign, False, False)
        number_country_code = int(phone_validation.phone_parse(format_number, None).country_code)
        country = self.env['res.country'].search([('phone_code', '=', number_country_code)])
        if not number and not format_number:
            return self.env['res.partner']
        partner = self.env['res.partner'].search(
            ['|', ('mobile', '=', format_number), ('phone', '=', format_number)],
            limit=1
        )
        if not partner:
            partner = self.env['res.partner'].create({
                'name': name or format_number,
                'mobile': format_number,
                'country_id': country.id if country else False,
            })
            partner._message_log(
                body=_("Partner created by incoming WhatsApp message.")
            )
        return partner
