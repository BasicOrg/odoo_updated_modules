# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _lt, _

PROXY_ERROR_CODES = {
    "error_codabox_not_configured": _lt("Codabox is not configured. Please check your configuration."),
    "error_connecting_iap": _lt("Error while connecting to the IAP server. Please contact Odoo support."),
    "error_fidu_registered_no_iap_token": _lt("It seems that you have already registered this fiduciary. You must reuse the same access token to connect to Codabox."),
    "error_fidu_registered_invalid_iap_token": _lt("The provided access token is not valid for this fiduciary. Please check your configuration.\nIf you have lost your access token, please contact Odoo support."),
    "error_connecting_codabox": _lt("Error while connecting to Codabox. Please contact Odoo support."),
    "error_connection_not_found": _lt("It seems that no connection linked to your database/VAT number exists. Please check your configuration."),
    "error_consent_not_valid": _lt("It seems that your Codabox connection is not valid anymore.  Please check your configuration."),
}

CODABOX_ERROR_CODES = {
    "notFound": _lt("No files were found. Please check your configuration."),
    "validationError": _lt("It seems that the company or fiduciary VAT number you provided is not valid. Please check your configuration."),
    "unknownAccountingOffice": _lt("It seems that the fiduciary VAT number you provided does not exist in Codabox. Please check your configuration."),
    "alreadyRegistered": _lt("It seems you have already created a connection to Codabox with this fiduciary. To create a new connection, you must first revoke the old one on myCodabox portal."),
    "timeout": _lt("Codabox is not responding. Please try again later."),
}

DEFAULT_IAP_ENDPOINT = "https://l10n-be-codabox.api.odoo.com/api/l10n_be_codabox/1"


def get_error_msg(error):
    error_type = error.get("type")
    codabox_error_code = error.get("codabox_error_code")
    if error_type == 'error_connecting_codabox' and codabox_error_code:
        return CODABOX_ERROR_CODES.get(codabox_error_code, _("Unknown error %s while contacting Codabox. Please contact Odoo support.", codabox_error_code))
    return PROXY_ERROR_CODES.get(error_type, _("Unknown error %s while contacting Codabox. Please contact Odoo support.", error_type))


def get_iap_endpoint(env):
    return env["ir.config_parameter"].sudo().get_param("l10n_be_codabox.iap_endpoint", DEFAULT_IAP_ENDPOINT)
