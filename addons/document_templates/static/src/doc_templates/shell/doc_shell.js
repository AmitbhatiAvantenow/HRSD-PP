import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

const FULLSCREEN_BODY_CLASS = "o_doctpl_fullscreen";

export const NAV_ITEMS = [
    { key: "dashboard", label: "Dashboard", action: "document_templates.action_doc_dashboard", group: "Overview", icon: "fa-dashboard" },

    { key: "templates", label: "Templates", action: "document_templates.action_doc_templates", group: "Library", icon: "fa-file-text-o" },
    { key: "categories", label: "Categories", action: "document_templates.action_doc_categories", group: "Library", icon: "fa-tags" },
    { key: "variables", label: "Variables", action: "document_templates.action_doc_variables", group: "Library", icon: "fa-code" },

    { key: "generated", label: "Generated Documents", action: "document_templates.action_doc_generated", group: "Activity", icon: "fa-download" },
    { key: "approval_workflow", label: "Approval Workflow", action: "document_templates.action_doc_approval_workflow", group: "Activity", icon: "fa-check-square-o" },
    { key: "shared_templates", label: "Shared Templates", action: "document_templates.action_doc_shared_templates", group: "Activity", icon: "fa-share-alt" },
    { key: "favourite_templates", label: "Favourite Templates", action: "document_templates.action_doc_favourite_templates", group: "Activity", icon: "fa-star" },

    { key: "ai_generator_stub", label: "AI Template Generator", action: "document_templates.action_doc_ai_generator_stub", group: "More", icon: "fa-magic", badge: "Soon" },
    { key: "marketplace_stub", label: "Template Marketplace", action: "document_templates.action_doc_marketplace_stub", group: "More", icon: "fa-shopping-bag", badge: "Soon" },
    { key: "settings", label: "Settings", action: "document_templates.action_doc_settings", group: "More", icon: "fa-cog" },
];

export class DocShell extends Component {
    static template = "document_templates.DocShell";
    static props = {
        activeKey: String,
        eyebrow: String,
        title: String,
        subtitle: { type: String, optional: true },
        footerModule: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.navItems = NAV_ITEMS;
        this.state = useState({ companyName: "", userName: user.name || "", collapsed: false });

        onWillStart(async () => {
            const companies = await this.orm.searchRead("res.company", [], ["name"], { limit: 1 });
            this.state.companyName = companies[0]?.name || "";
        });

        onMounted(() => document.body.classList.add(FULLSCREEN_BODY_CLASS));
        onWillUnmount(() => document.body.classList.remove(FULLSCREEN_BODY_CLASS));
    }

    get groupedNav() {
        const groups = [];
        const byName = new Map();
        for (const item of this.navItems) {
            let group = byName.get(item.group);
            if (!group) {
                group = { name: item.group, items: [] };
                byName.set(item.group, group);
                groups.push(group);
            }
            group.items.push(item);
        }
        return groups;
    }

    go(item) {
        if (item.key === this.props.activeKey) return;
        this.action.doAction(item.action);
    }

    toggleCollapse() {
        this.state.collapsed = !this.state.collapsed;
    }
}
