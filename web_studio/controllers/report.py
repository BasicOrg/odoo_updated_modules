# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from lxml import etree, html
from psycopg2 import OperationalError

from odoo import http, _, Command, models
from odoo.http import request, serialize_exception
from odoo.addons.web_studio.controllers import main
from odoo.tools.safe_eval import safe_eval

def api_tree_or_string(func):
    def from_tree_or_string(tree_or_string, *args, **kwargs):
        is_string = isinstance(tree_or_string, str)
        tree = html.fromstring(tree_or_string) if is_string else tree_or_string
        res = func(tree, *args, **kwargs)
        return html.tostring(res) if is_string else tree
    return from_tree_or_string

def _transform_table(table):
    for el in table.xpath(".|.//thead|.//tbody|.//tfoot|.//th|.//tr|.//td"):
        tag = el.tag
        el.set("oe-origin-tag", tag)
        el.tag = "div"
        el.set("oe-origin-style", el.attrib.pop("style", ""))

@api_tree_or_string
def _html_to_client_compliant(tree):
    for table in tree.xpath("//table[descendant-or-self::t[not(ancestor::td)]]"):
        _transform_table(table)

    return tree

@api_tree_or_string
def _cleanup_from_client(tree):
    tree = _to_qweb(tree)
    for el in tree.xpath("//*[@oe-context]"):
        el.attrib.pop("oe-context")

    for el in tree.xpath("//*[@oe-expression-readable]"):
        el.attrib.pop("oe-expression-readable")

    for el in tree.xpath("//img[@t-att-src]"):
        el.attrib.pop("src")

    return tree

@api_tree_or_string
def _to_qweb(tree):
    for el in tree.xpath("//*[@*[starts-with(name(), 'oe-origin-')]]"):
        for att in el.attrib:
            if not att.startswith("oe-origin-"):
                continue
            origin_name = att[10:]
            att_value = el.attrib.pop(att)
            if origin_name == "tag":
                el.tag = att_value
            else:
                if att_value:
                    el.set(origin_name, att_value)
                elif origin_name in el.attrib:
                    el.attrib.pop(origin_name)

    return tree

def human_readable_dotted_expr(env, model, chain):
    chain.reverse()
    human_readable = []

    while chain and model is not None:
        fname = chain.pop()
        field = model._fields[fname] if fname in model._fields else None
        if field is not None:
            human_readable.append(field.get_description(env, ["string"])["string"])
            model = env[field.comodel_name] if field.comodel_name else None
        else:
            model = None
            human_readable.append(fname.split("(")[0])

    human_readable.extend(reversed(chain))

    return human_readable

def parse_simple_dotted_expr(expr):
    parsed = []
    fn_level = 0

    single_expr = []
    for char in expr:
        if char == "." and not fn_level:
            parsed.append("".join(single_expr))
            single_expr = []
            continue

        elif char == '(':
            fn_level += 1

        elif char == ')':
            fn_level -= 1

        single_expr.append(char)

    parsed.append("".join(single_expr))

    return parsed

def expr_to_simple_chain(expr, env, main_model, qcontext):
    chain = parse_simple_dotted_expr(expr)
    if not chain:
        return ""
    model = qcontext[chain[0]] if chain[0] in qcontext else None
    if model is not None and hasattr(model, "_name") and model._name in env:
        model_description = None
        if model._name != main_model:
            model_description = env["ir.model"]._get(model._name).name
        new_chain = [model_description] if model_description else []
        new_chain.extend(human_readable_dotted_expr(env, model, chain[1:]))
        return " > ".join(new_chain) if new_chain else ""
    else:
        return ""

@api_tree_or_string
def _guess_qweb_variables(tree, report, qcontext):
    qcontext = dict(qcontext)
    keys_info = {}
    env = report.env
    qcontext["company"] = env.company
    IrQweb = env["ir.qweb"]

    def qweb_like_eval(expr, values, is_format=False):
        qcontext = {"values": values}
        if not is_format:
            compiled = IrQweb._compile_expr(expr)
        else:
            qcontext["self"] = IrQweb
            compiled = IrQweb._compile_format(expr)
        return safe_eval(compiled, qcontext)

    def qweb_like_string_eval(expr, qcontext, is_format=False):
        try:
            return qweb_like_eval(expr, qcontext, is_format) or ""
        except OperationalError:
            raise
        except Exception: # pylint: disable=W0718,W0703
            pass
        return ""

    def apply_oe_context(node, qcontext, keys_info):
        oe_context = {}
        for k, v in qcontext.items():
            try:
                if v._name in env:
                    oe_context[k] = {
                        "model":  v._name,
                        "name": env["ir.model"]._get(v._name).name,
                        "in_foreach": keys_info.get(k, {}).get("in_foreach", False)
                    }
            # Don't even warn: we just want models in the context
            # pylint: disable=W0702
            except:
                continue
        node.set("oe-context", json.dumps(oe_context))

    def recursive(node, qcontext, keys_info):
        if "t-foreach" in node.attrib:
            expr = node.get("t-foreach")
            # compile
            new_var = node.get("t-as")
            qcontext = dict(qcontext)
            keys_info = dict(keys_info)
            try:
                qcontext[new_var] = qweb_like_eval(expr, qcontext)
                keys_info[new_var] = {"in_foreach": True, "type": "python"}
            except OperationalError:
                raise
            except Exception: # pylint: disable=W0718,W0703
                pass
            apply_oe_context(node, qcontext, keys_info)

        if "t-set" in node.attrib and "t-value" in node.attrib:
            new_var = node.get("t-set")
            expr = node.get("t-value")
            try:
                evalled = qweb_like_eval(expr, qcontext)
                if new_var not in qcontext or not isinstance(evalled, type(qcontext[new_var])):
                    keys_info[new_var] = {"type": "python"}
                qcontext[new_var] = evalled
            except OperationalError:
                raise
            except Exception: # pylint: disable=W0718,W0703
                pass
            apply_oe_context(node, qcontext, keys_info)

        if "t-attf-class" in node.attrib or "t-att-class" in node.attrib:
            klass = node.get("class", "")
            node.set("oe-origin-class", klass)

            new_class = ""
            if "t-att-class" in node.attrib:
                expr = node.get("t-att-class")
                new_class += qweb_like_string_eval(expr, qcontext)

            if "t-attf-class" in node.attrib:
                expr = node.get("t-attf-class")
                new_class += qweb_like_string_eval(expr, qcontext, is_format=True)

            node.set("class", new_class)

        if "t-field" in node.attrib:
            expr = node.get("t-field")
            human_readable = expr_to_simple_chain(expr, env, report.model, qcontext) or "Field"
            node.set("oe-expression-readable", human_readable)

        tout = [att for att in ("t-out", "t-esc") if att in node.attrib]
        if tout and not node.get(tout[0]) == "0":
            expr = node.get(tout[0])
            human_readable = expr_to_simple_chain(expr, env, report.model, qcontext) or "Expression"
            node.set("oe-expression-readable", human_readable)

        if node.tag == "img" and ("t-att-src" in node.attrib):
            src = node.get("t-att-src")
            is_company_logo = src == "image_data_uri(company.logo)"
            placeholder = f'/logo.png?company={env.company.id}' if is_company_logo else'/web/static/img/placeholder.png'
            src = qweb_like_string_eval(src, qcontext) or placeholder
            node.set("src", src)

        if node.get("id") == "wrapwrap":
            apply_oe_context(node, qcontext, keys_info)

        for child in node:
            recursive(child, qcontext, keys_info)

    recursive(tree, qcontext, keys_info)
    return tree

VIEW_BACKUP_KEY = "web_studio.__backup__._{view.id}_._{view.key}_"

def get_report_view_copy(view):
    key = VIEW_BACKUP_KEY.format(view=view)
    return view.with_context(active_test=False).search([("key", "=", key)], limit=1)

def _copy_report_view(view):
    copy = get_report_view_copy(view)
    if not copy:
        key = VIEW_BACKUP_KEY.format(view=view)
        copy = view.copy({
            "name": f"web_studio_backup__{view.name}",
            "inherit_id": False,
            "mode": "primary",
            "key": key,
            "active": False,
        })
    return copy


class WebStudioReportController(main.WebStudioController):

    @http.route('/web_studio/create_new_report', type='json', auth='user')
    def create_new_report(self, model_name, layout, context=None):
        if context:
            request.update_context(**context)

        if layout == 'web.basic_layout':
            arch_document = etree.fromstring("""
                <t t-name="studio_report_document">
                    <div class="page"><br/></div>
                </t>
                """)
        else:
            arch_document = etree.fromstring("""
                <t t-name="studio_report_document">
                    <t t-call="%(layout)s">
                        <div class="page"><br/></div>
                    </t>
                </t>
                """ % {'layout': layout})

        view_document = request.env['ir.ui.view'].create({
            'name': 'studio_report_document',
            'type': 'qweb',
            'arch': etree.tostring(arch_document, encoding='utf-8', pretty_print=True),
        })

        new_view_document_xml_id = view_document.get_external_id()[view_document.id]
        view_document.name = '%s_document' % new_view_document_xml_id
        view_document.key = '%s_document' % new_view_document_xml_id

        if layout == 'web.basic_layout':
            arch = etree.fromstring("""
                <t t-name="studio_main_report">
                    <t t-foreach="docs" t-as="doc">
                        <t t-call="%(layout)s">
                            <t t-call="%(document)s_document"/>
                            <p style="page-break-after: always;"/>
                        </t>
                    </t>
                </t>
            """ % {'layout': layout, 'document': new_view_document_xml_id})
        else:
            arch = etree.fromstring("""
                <t t-name="studio_main_report">
                    <t t-call="web.html_container">
                        <t t-foreach="docs" t-as="doc">
                            <t t-call="%(document)s_document"/>
                        </t>
                    </t>
                </t>
            """ % {'document': new_view_document_xml_id})

        view = request.env['ir.ui.view'].create({
            'name': 'studio_main_report',
            'type': 'qweb',
            'arch': etree.tostring(arch, encoding='utf-8', pretty_print=True),
        })
        # FIXME: When website is installed, we need to set key as xmlid to search on a valid domain
        # See '_view_obj' in 'website/model/ir.ui.view'
        view.name = new_view_document_xml_id
        view.key = new_view_document_xml_id

        model = request.env['ir.model']._get(model_name)
        report = request.env['ir.actions.report'].create({
            'name': _('%s Report', model.name),
            'model': model.model,
            'report_type': 'qweb-pdf',
            'report_name': view.name,
        })
        # make it available in the print menu
        report.create_action()

        return {
            'id': report.id,
            'display_name': report.display_name,
            'report_name': report.name,
        }

    @http.route('/web_studio/print_report', type='json', auth='user')
    def print_report(self, report_id, record_id):
        report = request.env['ir.actions.report'].with_context(report_pdf_no_attachment=True, discard_logo_check=True)._get_report(report_id)
        return report.report_action(record_id)

    @http.route('/web_studio/load_report_editor', type='json', auth='user')
    def load_report_editor(self, report_id, fields, context=None):
        if context:
            request.update_context(**context)
        report = request.env['ir.actions.report'].browse(report_id)
        report_data = report.read(fields)
        paperformat = report._read_paper_format_measures()

        qweb_error = None
        try:
            report_qweb = self._get_report_qweb(report)
        except ValueError as e:
            if (hasattr(e, "context") and isinstance(e.context.get("view"), models.BaseModel)):
                # This is coming from _raise_view_error, don't crash
                report_qweb = None
                qweb_error = serialize_exception(e)
            else:
                raise e

        return {
            "report_data": report_data and report_data[0],
            "paperformat": paperformat,
            "report_qweb": report_qweb,
            "qweb_error": qweb_error,
        }

    @http.route('/web_studio/get_report_html', type='json', auth='user')
    def get_report_html(self, report_id, record_id, context=None):
        if context:
            request.update_context(**context)
        report = request.env['ir.actions.report'].browse(report_id)
        report_html = self._render_report(report, record_id)
        return report_html and report_html[0]

    @http.route('/web_studio/get_report_qweb', type='json', auth='user')
    def get_report_qweb(self, report_id, context=None):
        if context:
            request.update_context(**context)
        report = request.env['ir.actions.report'].browse(report_id)
        return self._get_report_qweb(report)

    def _get_report_qweb(self, report):
        loaded = {}
        report = report.with_context(studio=True)
        report_name = report.report_name
        IrQweb = request.env["ir.qweb"].with_context(studio=True, inherit_branding=True, lang=None)

        def inline_t_call(tree, variables):
            if variables:
                touts = tree.xpath("//t[@t-out='0']")
                for node in touts:
                    val = variables.get("__zero__")
                    if not val:
                        continue
                    subtree = etree.fromstring(val)
                    for child in subtree:
                        node.append(child)
                    node.attrib.pop("t-out")

            if not variables:
                variables = dict()
            for node in tree.xpath("//*[@t-call]"):
                tcall = node.get("t-call")
                if '{' in tcall:
                    # this t-call value is dynamic (e.g. t-call="{{company.tmp}})
                    # so its corresponding view cannot be read
                    # this template won't be returned to the Editor so it won't
                    # be customizable
                    continue

                _vars = dict(variables)
                z = etree.Element("t", {'process_zero': "1"})
                for child in node:
                    if not child.get("t-set"):
                        z.append(child)
                if len(z) > 0:
                    _vars["__zero__"] = etree.tostring(z)

                sub_element = load_arch(tcall, _vars)
                node.append(sub_element)

        def load_arch(view_name, variables=None):
            if not variables:
                variables = dict()
            if view_name in loaded:
                tree = etree.fromstring(loaded[view_name])
            elif view_name == "web.external_layout":
                external_layout = "web.external_layout_standard"
                if request.env.company.external_report_layout_id:
                    external_layout = request.env.company.external_report_layout_id.sudo().key
                tree = load_arch(external_layout, variables)
            else:
                tree = IrQweb._get_template(view_name)[0]
                loaded[view_name] = etree.tostring(tree)

            inline_t_call(tree, variables)
            return tree

        main_qweb = _html_to_client_compliant(load_arch(report_name))

        render_context = report._get_rendering_context(report, [0], {"studio": True})
        render_context['report_type'] = "pdf"
        main_qweb = _guess_qweb_variables(main_qweb, report, render_context)

        html_container = request.env["ir.ui.view"]._render_template("web.html_container", {"studio": True})
        html_container = html.fromstring(html_container)
        main_qweb.xpath("//*[@id='wrapwrap']")[0]
        wrap = html_container.xpath("//*[@id='wrapwrap']")[0]
        wrap.getparent().replace(wrap, main_qweb.xpath("//*[@id='wrapwrap']")[0])

        return html.tostring(html_container)

    def _render_report(self, report, record_id):
        return request.env['ir.actions.report'].with_context(studio=True)._render_qweb_html(report, [record_id] if record_id else [], {"studio": True})

    @http.route("/web_studio/save_report", type="json", auth="user")
    def save_report(self, report_id, report_changes=None, html_parts=None, xml_verbatim=None, record_id=None, context=None):
        if context:
            request.update_context(**context)
        report_data = None
        paperformat = None
        report = request.env["ir.actions.report"].browse(report_id)

        if report_changes:
            to_write = dict(report_changes)
            if to_write["display_in_print_menu"] is True:
                to_write["binding_model_id"] = to_write["binding_model_id"][0] if to_write["binding_model_id"] else report.model_id
            else:
                to_write["binding_model_id"] = False
            del to_write["display_in_print_menu"]

            if to_write["attachment_use"]:
                to_write["attachment"] = f"'{report.name}'"
            else:
                to_write["attachment"] = False

            to_write["paperformat_id"] = to_write["paperformat_id"][0] if to_write["paperformat_id"] else False

            to_write["groups_id"] = [Command.clear()] + [Command.link(_id) for _id in to_write["groups_id"]]
            report.write(to_write)
            report_data = report.read(to_write.keys())
            paperformat = report._read_paper_format_measures()

        IrView = request.env["ir.ui.view"].with_context(studio=True, no_cow=True, lang=None)
        xml_ids = request.env["ir.model.data"]
        if html_parts:
            for view_id, data in html_parts.items():
                view = IrView.browse(int(view_id))
                _copy_report_view(view)
                for xpath, escaped_html in data.items():
                    if xpath == "entire_view":
                        xpath = "."
                    view.save(_cleanup_from_client(escaped_html), xpath)
                xml_ids = xml_ids | view.model_data_id

        if xml_verbatim:
            for view_id, arch in xml_verbatim.items():
                view = IrView.browse(int(view_id))
                _copy_report_view(view)
                view.write({"arch": arch})
                xml_ids = xml_ids | view.model_data_id

        if report_changes or html_parts or xml_verbatim:
            xml_ids |= request.env['ir.model.data'].sudo().search(["&", ("model", "=", report._name), ("res_id", "=", report.id)])


        if xml_ids:
            xml_ids.write({"noupdate": True})

        # We always try to render the full report here because in case of failure, we need
        # the transaction to rollback
        report_html = self._render_report(report, record_id)
        report_qweb = self._get_report_qweb(report)

        return {
            "report_qweb": report_qweb,
            "report_html": report_html and report_html[0],
            "paperformat": paperformat,
            "report_data": report_data and report_data[0],
        }

    @http.route("/web_studio/reset_report_archs", type="json", auth="user")
    def reset_report_archs(self, report_id, include_web_layout=True):
        report = request.env["ir.actions.report"].browse(report_id)
        views = request.env["ir.ui.view"].with_context(no_primary_children=True, __views_get_original_hierarchy=[], no_cow=True).get_related_views(report.report_name, bundles=False)
        if not include_web_layout:
            views = views.filtered(lambda v: not v.key.startswith("web.") or "layout" not in v.key)
        views.reset_arch(mode="hard")
        return True
