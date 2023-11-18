/** @odoo-module */

import { _t } from '@web/core/l10n/translation';
import { decodeDataBehaviorProps, getVideoUrl } from '@knowledge/js/knowledge_utils';
import { registry } from "@web/core/registry";

/**
 * Set of all the classes that needs to be cleaned before saving the article
 */
const DECORATION_CLASSES = new Set([
    'o_knowledge_header_highlight',
    'focused-comment'
]);
/**
 * Plugin for OdooEditor. This plugin will allow us to clean/transform the
 * document before saving it in the database.
 */
export class KnowledgePlugin {
    constructor ({ editor }) {
        this.editor = editor;
    }
    /**
     * Remove the highlight decorators from the document and replace the video
     * iframe with a video link before saving. The method aims to solve the
     * following issues:
     * (1) Some components are susceptible to add classes that are meant to be purely for decoration
     *     or highlighting of specific anchors in the text. These classes shouldn't be saved because
     *     they serve no real purpose other than highlight the text or decorate it temporarily.
     * (2) When saving the document, the sanitizer discards the video iframe
     *     from the document. As a result, people reading the article outside
     *     of the odoo backend will not be able to see and access the video.
     *     To solve that issue, we will replace the iframe with a link before
     *     saving.
     * @param {Element} editable
     */
    cleanForSave(editable) {
        // Remove the decoration classes from the editable:
        for (const decorationClass of DECORATION_CLASSES) {
            for (const elementToClean of editable.querySelectorAll(`.${decorationClass}`)) {
                elementToClean.classList.remove(decorationClass);
            }
        }
        // Replace the iframe with a video link:
        for (const anchor of editable.querySelectorAll('.o_knowledge_behavior_type_video')) {
            const props = decodeDataBehaviorProps(anchor.dataset.behaviorProps);
            const a = document.createElement('a');
            a.href = getVideoUrl(props.platform, props.videoId, props.params);
            a.textContent = _t('Open Video');
            a.target = '_blank';
            while (anchor.firstChild) {
                anchor.removeChild(anchor.firstChild);
            }
            anchor.append(a);
        }
        // Remove the `d-none` class of the fileName element in case the
        // html_field is being saved while the user is editing the name of the
        // file (The input is removed by default because it is the child of a
        // data-oe-transient-content="true" node).
        for (const fileNameEl of editable.querySelectorAll('.o_knowledge_behavior_type_file .o_knowledge_file_name')) {
            fileNameEl.classList.remove("d-none");
        }
    }
}

registry.category("wysiwygPlugins").add("Knowledge", KnowledgePlugin);
