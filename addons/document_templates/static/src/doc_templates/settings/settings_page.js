import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";
import { ModernSelect } from "../widgets/modern_select";

export class SettingsPage extends Component {
    static template = "document_templates.SettingsPage";
    static components = { DocShell, ModernSelect };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            saving: false,
            saved: false,
            default_access_level: "private",
        });

        onWillStart(async () => {
            const settings = await this.orm.call("document.template", "get_settings", []);
            Object.assign(this.state, settings);
        });
    }

    get accessLevelOptions() {
        return [
            { value: "private", label: "Private (only me)" },
            { value: "team", label: "Team (my department)" },
            { value: "company", label: "Company-wide" },
        ];
    }

    onAccessLevelSelect(v) {
        this.state.default_access_level = v;
    }

    async save() {
        this.state.saving = true;
        try {
            await this.orm.call("document.template", "set_settings", [{
                default_access_level: this.state.default_access_level,
            }]);
            this.state.saved = true;
            setTimeout(() => { this.state.saved = false; }, 2000);
        } finally {
            this.state.saving = false;
        }
    }
}

registry.category("actions").add("doc_settings", SettingsPage);
