/** @odoo-module */

import { isEmptyBlock } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { useBus } from '@web/core/utils/hooks';
import {
    isZWS,
    getDeepRange,
    getSelectedNodes,
    closestElement,
} from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { useRef } from '@odoo/owl';

/**
 * This widget will extend Wysiwyg and contain all code that are specific to
 * Knowledge and that should not be included in the global Wysiwyg instance.
 *
 * Note: The utils functions of the OdooEditor are included in a different bundle
 * asset than 'web.assets_backend'. We can therefore not import them in the
 * backend code of Knowledge. This widget will be allow us to use them.
 */
export class KnowledgeWysiwyg extends Wysiwyg {
    static template = 'knowledge.KnowledgeWysiwyg';

    setup() {
        super.setup(...arguments);
        useBus(this.env.bus, 'KNOWLEDGE_WYSIWYG:HISTORY_STEP', () => this.odooEditor.historyStep());
        this.knowledgeCommentsToolbarBtnRef = useRef('knowledgeCommentsToolbarBtn');
    }

    /**
     * Configure the new buttons added inside the knowledge toolbar.
     * @override
     * @param {*} options
     */
    _configureToolbar(options) {
        this.knowledgeCommentsToolbarBtnRef.el?.addEventListener('click', () => {
            getDeepRange(this.$editable[0], { splitText: true, select: true, correctTripleClick: true });
            const selectedNodes = getSelectedNodes(this.$editable[0])
                .filter(selectedNode => selectedNode.nodeType === Node.TEXT_NODE && closestElement(selectedNode).isContentEditable);
            this.env.bus.trigger('KNOWLEDGE:CREATE_COMMENT_THREAD', {selectedNodes});
        });
        super._configureToolbar(...arguments);
    }

    _onSelectionChange() {
        const selection = document.getSelection();
        if (selection.type === "None") {
            super._onSelectionChange(...arguments);
            return;
        }
        const selectedNodes = getSelectedNodes(this.$editable[0]);
        const btnHidden = selectedNodes.length && selectedNodes.every((node) => isZWS(node) || !closestElement(node)?.isContentEditable);
        this.knowledgeCommentsToolbarBtnRef.el?.classList.toggle('d-none', btnHidden);
        super._onSelectionChange(...arguments);
    }

    /**
     * @override
     */
    async startEdition() {
        await super.startEdition(...arguments);
        this.odooEditor.options.renderingClasses = [...this.odooEditor.options.renderingClasses, 'focused-comment'];
    }

    /**
     * Checks if the editable zone of the editor is empty.
     * @returns {boolean}
     */
    isEmpty() {
        return this.$editable[0].children.length === 1 && isEmptyBlock(this.$editable[0].firstElementChild);
    }
}
