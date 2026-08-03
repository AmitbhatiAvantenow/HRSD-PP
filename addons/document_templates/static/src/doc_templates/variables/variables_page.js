import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";

const VARIABLE_TYPES = [
    { value: "text", label: "Text" },
    { value: "long_text", label: "Long Text" },
    { value: "number", label: "Number" },
    { value: "currency", label: "Currency" },
    { value: "date", label: "Date" },
    { value: "boolean", label: "Yes/No" },
];

export class VariablesPage extends Component {
    static template = "document_templates.VariablesPage";
    static components = { DocShell };

    setup() {
        this.orm = useService("orm");
        this.variableTypes = VARIABLE_TYPES;
        this.state = useState({
            variables: [],
            templates: [],
            showAddForm: false,
            newVarTemplateId: "",
            newVarName: "",
            newVarType: "text",
            newVarRequired: true,
            newVarDefault: "",
            newVarError: "",
        });

        onWillStart(async () => {
            await this.reload();
            this.state.templates = await this.orm.searchRead("document.template", [], ["name"], { order: "name" });
        });
    }

    async reload() {
        this.state.variables = await this.orm.searchRead(
            "document.template.variable", [], ["name", "key", "variable_type", "template_id"],
            { order: "template_id" });
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

    variableTypeLabel(type) {
        return (this.variableTypes.find((t) => t.value === type) || {}).label || type;
    }

    toggleAddForm() {
        this.state.showAddForm = !this.state.showAddForm;
        this.state.newVarError = "";
    }

    async createVariable() {
        this.state.newVarError = "";
        const templateId = parseInt(this.state.newVarTemplateId, 10);
        const name = this.state.newVarName.trim();
        if (!templateId) {
            this.state.newVarError = "Pick which template this variable belongs to.";
            return;
        }
        if (!name) {
            this.state.newVarError = "Give the variable a name.";
            return;
        }
        const key = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
        if (!key) return;
        const clash = this.state.variables.some((v) => v.template_id[0] === templateId && v.key === key);
        if (clash) {
            this.state.newVarError = "A variable with this name already exists on that template.";
            return;
        }
        await this.orm.create("document.template.variable", [{
            template_id: templateId,
            name,
            key,
            variable_type: this.state.newVarType,
            is_required: this.state.newVarRequired,
            default_value: this.state.newVarDefault || false,
        }]);
        await this.reload();
        this.state.newVarName = "";
        this.state.newVarType = "text";
        this.state.newVarRequired = true;
        this.state.newVarDefault = "";
    }

    async deleteVariable(v) {
        await this.orm.unlink("document.template.variable", [v.id]);
        await this.reload();
    }
}

registry.category("actions").add("doc_variables", VariablesPage);
