import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ModernSelect } from "../widgets/modern_select";

export class ShareDialog extends Component {
    static template = "document_templates.ShareDialog";
    static components = { Dialog, ModernSelect };
    static props = {
        templateId: Number,
        templateName: { type: String, optional: true },
        onShared: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ saving: false, error: "", users: [], sharedUserIds: [] });

        onWillStart(async () => {
            const [template, users] = await Promise.all([
                this.orm.read("document.template", [this.props.templateId], ["shared_user_ids"]),
                this.orm.searchRead("res.users", [], ["name", "login"]),
            ]);
            this.state.users = users;
            this.state.sharedUserIds = (template[0]?.shared_user_ids || []).map(String);
        });
    }

    get userOptions() {
        const selected = new Set(this.state.sharedUserIds);
        return this.state.users
            .filter((u) => !selected.has(String(u.id)))
            .map((u) => ({ value: String(u.id), label: u.name, sublabel: u.login }));
    }
    get sharedUsers() {
        return this.state.sharedUserIds
            .map((id) => this.state.users.find((u) => String(u.id) === String(id)))
            .filter(Boolean);
    }

    addUser(v) {
        if (v && !this.state.sharedUserIds.includes(v)) {
            this.state.sharedUserIds = [...this.state.sharedUserIds, v];
        }
    }
    removeUser(id) {
        this.state.sharedUserIds = this.state.sharedUserIds.filter((u) => u !== String(id));
    }

    async save() {
        this.state.saving = true;
        this.state.error = "";
        try {
            const vals = { shared_user_ids: [[6, 0, this.state.sharedUserIds.map((id) => parseInt(id, 10))]] };
            if (this.state.sharedUserIds.length) {
                vals.access_level = "team";
            }
            await this.orm.write("document.template", [this.props.templateId], vals);
            this.props.onShared?.();
            this.props.close();
        } catch (e) {
            this.state.error = e.message?.data?.message || "Could not share template.";
        } finally {
            this.state.saving = false;
        }
    }

    cancel() {
        this.props.close();
    }
}
