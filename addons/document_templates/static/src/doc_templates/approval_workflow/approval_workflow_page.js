import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";
import { TemplateGrid } from "../templates/template_grid";

export class ApprovalWorkflowPage extends Component {
    static template = "document_templates.ApprovalWorkflowPage";
    static components = { DocShell, TemplateGrid };

    get domainExtra() {
        return [["approval_state", "!=", "none"]];
    }
}

registry.category("actions").add("doc_approval_workflow", ApprovalWorkflowPage);
