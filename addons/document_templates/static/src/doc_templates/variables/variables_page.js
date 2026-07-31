import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";

export class VariablesPage extends Component {
    static template = "document_templates.VariablesPage";
    static components = { DocShell };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ variables: [] });

        onWillStart(async () => {
            this.state.variables = await this.orm.searchRead(
                "document.template.variable", [], ["name", "key", "variable_type", "template_id"],
                { order: "template_id" });
        });
    }

    get groupedByTemplate() {
        const groups = [];
        const byId = new Map();
        for (const v of this.state.variables) {
            const templateId = v.template_id[0];
            const templateName = v.template_id[1];
            let group = byId.get(templateId);
            if (!group) {
                group = { templateId, templateName, items: [] };
                byId.set(templateId, group);
                groups.push(group);
            }
            group.items.push(v);
        }
        return groups;
    }
}

registry.category("actions").add("doc_variables", VariablesPage);
