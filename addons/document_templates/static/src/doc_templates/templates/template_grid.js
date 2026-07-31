import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { ModernSelect } from "../widgets/modern_select";
import { PreviewDialog } from "./preview_dialog";
import { ShareDialog } from "./share_dialog";
import { GenerateDialog } from "./generate_dialog";

const ACCENT_COLORS = ["--doc-primary", "--doc-info", "--doc-success", "--doc-warning", "--doc-purple", "--doc-danger"];
const AVATAR_COLORS = ["#4453c9", "#3f8fd6", "#2f8f5b", "#b9860f", "#8b5fd6", "#c0392b"];

function hashString(str) {
    let hash = 0;
    for (let i = 0; i < (str || "").length; i++) {
        hash = (hash << 5) - hash + str.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash);
}

function relativeTime(dateStr) {
    if (!dateStr) return "";
    // Odoo datetime strings are UTC without a timezone suffix.
    const then = new Date(dateStr.replace(" ", "T") + "Z");
    const diffMs = Date.now() - then.getTime();
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min${mins === 1 ? "" : "s"} ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;
    return `${Math.floor(months / 12)} yr${Math.floor(months / 12) === 1 ? "" : "s"} ago`;
}

export class TemplateGrid extends Component {
    static template = "document_templates.TemplateGrid";
    static components = { ModernSelect };
    static props = {
        fetchMethod: { type: String, optional: true },
        domainExtra: { type: Array, optional: true },
        emptyLabel: { type: String, optional: true },
        showApprovalActions: { type: Boolean, optional: true },
    };
    static defaultProps = {
        fetchMethod: "get_grid_data",
        domainExtra: [],
        emptyLabel: "No templates found.",
        showApprovalActions: false,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.state = useState({
            search: "",
            templates: [],
            categories: [],
            categoryFilter: "",
            sort: "newest",
            viewMode: "grid",
            openMenuId: null,
        });

        onWillStart(async () => {
            this.state.categories = await this.orm.searchRead("document.template.category", [], ["name"], { order: "name" });
            await this.reload();
        });
    }

    async reload() {
        this.state.templates = await this.orm.call("document.template", this.props.fetchMethod, [
            this.props.domainExtra, this.state.search,
            this.state.categoryFilter ? parseInt(this.state.categoryFilter, 10) : false,
            this.state.sort,
        ]);
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.reload();
    }

    get categoryOptions() {
        return [{ value: "", label: "All Categories" }, ...this.state.categories.map((c) => ({ value: String(c.id), label: c.name }))];
    }
    get sortOptions() {
        return [
            { value: "newest", label: "Newest First" },
            { value: "name", label: "Name (A-Z)" },
            { value: "rating", label: "Highest Rated" },
            { value: "popular", label: "Most Used" },
        ];
    }
    onCategoryFilterSelect(v) {
        this.state.categoryFilter = v;
        this.reload();
    }
    onSortSelect(v) {
        this.state.sort = v;
        this.reload();
    }
    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    stars(rating) {
        return [1, 2, 3, 4, 5].map((n) => n <= Math.round(rating));
    }

    async setRating(t, n) {
        await this.orm.write("document.template", [t.id], { rating: n });
        this.reload();
    }

    accentColor(t) {
        return ACCENT_COLORS[hashString(t.category_name) % ACCENT_COLORS.length];
    }

    avatarInitials(name) {
        if (!name) return "?";
        const parts = name.trim().split(/\s+/);
        return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase() || name[0].toUpperCase();
    }
    avatarColor(name) {
        return AVATAR_COLORS[hashString(name) % AVATAR_COLORS.length];
    }
    relativeTime(dateStr) {
        return relativeTime(dateStr);
    }

    toggleMenu(t, ev) {
        ev.stopPropagation();
        this.state.openMenuId = this.state.openMenuId === t.id ? null : t.id;
    }
    closeMenu() {
        this.state.openMenuId = null;
    }

    openBuilder(t) {
        this.action.doAction("document_templates.action_doc_builder", {
            additionalContext: { default_template_id: t.id },
        });
    }

    previewTemplate(t) {
        this.dialog.add(PreviewDialog, { templateId: t.id, templateName: t.name });
    }

    useTemplate(t) {
        this.dialog.add(GenerateDialog, { templateId: t.id, onGenerated: () => this.reload() });
    }

    async duplicateTemplate(t) {
        this.closeMenu();
        await this.orm.call("document.template", "copy", [[t.id]]);
        this.reload();
    }

    async toggleFavorite(t) {
        await this.orm.call("document.template", "action_toggle_favorite", [[t.id]]);
        this.reload();
    }

    shareTemplate(t) {
        this.closeMenu();
        this.dialog.add(ShareDialog, { templateId: t.id, templateName: t.name, onShared: () => this.reload() });
    }

    async submitForApproval(t) {
        this.closeMenu();
        await this.orm.call("document.template", "action_submit_for_approval", [[t.id]]);
        this.reload();
    }

    async approveTemplate(t) {
        await this.orm.call("document.template", "action_approve", [[t.id]]);
        this.reload();
    }

    async rejectTemplate(t) {
        await this.orm.call("document.template", "action_reject", [[t.id]]);
        this.reload();
    }
}
