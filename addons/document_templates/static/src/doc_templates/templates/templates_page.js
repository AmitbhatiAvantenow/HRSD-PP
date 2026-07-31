import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";
import { TemplateGrid } from "./template_grid";
import { CreateTemplateWizard } from "./create_template_wizard";
import { UploadTemplateWizard } from "./upload_template_wizard";

export class TemplatesPage extends Component {
    static template = "document_templates.TemplatesPage";
    static components = { DocShell, TemplateGrid };

    setup() {
        this.dialog = useService("dialog");
        this.action = useService("action");
    }

    openBuilderFor(result) {
        if (result?.template_id) {
            this.action.doAction("document_templates.action_doc_builder", {
                additionalContext: { default_template_id: result.template_id },
            });
        }
    }

    openCreateWizard() {
        this.dialog.add(CreateTemplateWizard, { onCreated: (result) => this.openBuilderFor(result) });
    }

    openUploadWizard() {
        this.dialog.add(UploadTemplateWizard, { onCreated: (result) => this.openBuilderFor(result) });
    }
}

registry.category("actions").add("doc_templates", TemplatesPage);
