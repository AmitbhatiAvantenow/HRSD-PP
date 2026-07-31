import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ModernSelect } from "../widgets/modern_select";

export class GenerateDialog extends Component {
    static template = "document_templates.GenerateDialog";
    static components = { Dialog, ModernSelect };
    static props = {
        templateId: Number,
        initialValues: { type: Object, optional: true },
        initialPartnerId: { type: [Number, Boolean], optional: true },
        onGenerated: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            saving: false,
            error: "",
            templateName: "",
            variables: [],
            values: {},
            partners: [],
            partnerId: "",
            formats: { pdf: true, docx: false },
            result: null,
        });

        onWillStart(async () => {
            const [data, partners] = await Promise.all([
                this.orm.call("document.template", "get_generate_wizard_data", [this.props.templateId]),
                this.orm.searchRead("res.partner", [], ["name"], { limit: 300, order: "name" }),
            ]);
            this.state.templateName = data.template_name;
            this.state.variables = data.variables;
            this.state.partners = partners;
            const values = {};
            for (const v of data.variables) {
                values[v.key] = v.default_value || (v.variable_type === "boolean" ? false : "");
            }
            // Let a calling wizard (e.g. a Lease creation form) pre-fill any variables
            // whose key happens to match its own fields -- harmless no-op for keys the
            // template doesn't define.
            for (const [key, val] of Object.entries(this.props.initialValues || {})) {
                if (key in values && val !== undefined && val !== null && val !== "") {
                    values[key] = val;
                }
            }
            this.state.values = values;
            if (this.props.initialPartnerId) {
                this.state.partnerId = String(this.props.initialPartnerId);
            }
        });
    }

    get partnerOptions() {
        return this.state.partners.map((p) => ({ value: String(p.id), label: p.name }));
    }

    get isValid() {
        return this.state.variables.every((v) => !v.is_required || this.state.values[v.key] !== "")
            && (this.state.formats.pdf || this.state.formats.docx);
    }

    onPartnerSelect(v) {
        this.state.partnerId = v;
    }

    onValueInput(key, ev) {
        this.state.values[key] = ev.target.value;
    }

    onBooleanToggle(key) {
        this.state.values[key] = !this.state.values[key];
    }

    toggleFormat(fmt) {
        this.state.formats[fmt] = !this.state.formats[fmt];
    }

    async generate() {
        if (!this.isValid) return;
        this.state.saving = true;
        this.state.error = "";
        try {
            const formats = Object.keys(this.state.formats).filter((f) => this.state.formats[f]);
            const result = await this.orm.call("document.template", "action_generate", [
                [this.props.templateId], this.state.values, formats,
                this.state.partnerId ? parseInt(this.state.partnerId, 10) : false,
            ]);
            this.state.result = result;
            this.props.onGenerated?.(result);
        } catch (e) {
            this.state.error = e.message?.data?.message || "Could not generate document.";
        } finally {
            this.state.saving = false;
        }
    }

    close() {
        this.props.close();
    }
}
