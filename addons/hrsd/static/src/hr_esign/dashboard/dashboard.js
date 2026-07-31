import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const QUICK_ACTIONS = [
    { key: "create", icon: "fa-pencil-square-o", title: _t("Create Document"), desc: _t("Upload a PDF and start a new signing request"), color: "indigo" },
    { key: "documents", icon: "fa-folder-open", title: _t("Documents Workspace"), desc: _t("Track every document and its signing progress"), color: "blue" },
    { key: "templates", icon: "fa-copy", title: _t("Templates"), desc: _t("Reusable documents for common requests"), color: "violet" },
    { key: "workflows", icon: "fa-sitemap", title: _t("Active Workflows"), desc: _t("Documents currently awaiting signatures"), color: "orange" },
    { key: "audit", icon: "fa-shield", title: _t("Audit Logs"), desc: _t("Full event trail for every document"), color: "green" },
    { key: "reports", icon: "fa-line-chart", title: _t("Reports"), desc: _t("Turnaround time and completion analytics"), color: "pink" },
];

const KPI_CARDS = [
    { key: "pending_signatures", label: _t("Pending Signatures"), icon: "fa-pencil", color: "indigo" },
    { key: "completed_today", label: _t("Completed Today"), icon: "fa-check-circle", color: "green" },
    { key: "draft_documents", label: _t("Draft Documents"), icon: "fa-file", color: "blue" },
    { key: "waiting_approval", label: _t("Waiting Approval"), icon: "fa-hourglass-half", color: "orange" },
    { key: "rejected", label: _t("Rejected"), icon: "fa-times-circle", color: "red" },
    { key: "expiring_documents", label: _t("Expiring Soon"), icon: "fa-exclamation-triangle", color: "yellow" },
    { key: "active_workflows", label: _t("Active Workflows"), icon: "fa-sitemap", color: "violet" },
    { key: "total_documents", label: _t("Total Documents"), icon: "fa-cubes", color: "blue" },
];

const STATE_LABELS = {
    draft: _t("Draft"), sent: _t("Sent"), in_progress: _t("In Progress"),
    completed: _t("Completed"), rejected: _t("Rejected"), expired: _t("Expired"), archived: _t("Archived"),
};

const EVENT_ICONS = {
    created: { icon: "fa-file", color: "blue" },
    sent: { icon: "fa-paper-plane", color: "indigo" },
    viewed: { icon: "fa-eye", color: "violet" },
    signed: { icon: "fa-check", color: "green" },
    rejected: { icon: "fa-times", color: "red" },
    reminded: { icon: "fa-bell", color: "orange" },
    completed: { icon: "fa-check-circle", color: "green" },
    downloaded: { icon: "fa-download", color: "orange" },
    archived: { icon: "fa-archive", color: "gray" },
};

const FILE_ICONS = {
    pdf: { icon: "fa-file-pdf-o", color: "red" },
    doc: { icon: "fa-file-word-o", color: "blue" },
    docx: { icon: "fa-file-word-o", color: "blue" },
};

export class HrEsignDashboard extends Component {
    static template = "hrsd.HrEsignDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.quickActions = QUICK_ACTIONS;
        this.kpiCards = KPI_CARDS;
        this.stateLabels = STATE_LABELS;

        this.state = useState({
            loading: true,
            kpis: {},
            trends: {},
            recentDocuments: [],
            recentActivity: [],
            animate: false,
        });

        onWillStart(async () => {
            const data = await this.orm.call("hr.esign.document", "get_dashboard_data", []);
            this.state.kpis = data.kpis;
            this.state.trends = data.trends || {};
            this.state.recentDocuments = data.recent_documents;
            this.state.recentActivity = data.recent_activity;
            this.state.loading = false;
            setTimeout(() => { this.state.animate = true; }, 30);
        });
    }

    formatDuration(seconds) {
        if (!seconds) return "—";
        const m = Math.floor(seconds / 60);
        if (m < 1) return `${seconds}s`;
        if (m < 60) return `${m}m`;
        return `${Math.floor(m / 60)}h ${m % 60}m`;
    }

    /** SVG <polyline> points for a KPI card's 7-day sparkline (real daily counts). */
    sparklinePoints(key) {
        const values = this.state.trends[key] || [0, 0, 0, 0, 0, 0, 0];
        const max = Math.max(...values, 1);
        const w = 96;
        const h = 26;
        const step = w / (values.length - 1 || 1);
        return values
            .map((v, i) => `${(i * step).toFixed(1)},${(h - (v / max) * (h - 4) - 2).toFixed(1)}`)
            .join(" ");
    }

    eventMeta(eventType) {
        return EVENT_ICONS[eventType] || { icon: "fa-circle", color: "gray" };
    }

    fileMeta(fileName) {
        const ext = (fileName || "").split(".").pop().toLowerCase();
        return FILE_ICONS[ext] || { icon: "fa-file-o", color: "gray" };
    }

    /** Lightweight relative-time label ("2m ago", "1h ago", ...) from an Odoo datetime string. */
    timeAgo(datetimeStr) {
        if (!datetimeStr) return "";
        const then = new Date(datetimeStr.replace(" ", "T") + "Z").getTime();
        const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
        if (diffSec < 60) return _t("just now");
        const m = Math.floor(diffSec / 60);
        if (m < 60) return `${m}m ${_t("ago")}`;
        const h = Math.floor(m / 60);
        if (h < 24) return `${h}h ${_t("ago")}`;
        return `${Math.floor(h / 24)}d ${_t("ago")}`;
    }

    async onQuickAction(key) {
        if (key === "create") {
            return this.action.doAction({
                type: "ir.actions.client",
                tag: "hr_esign_create_wizard",
                name: _t("Create Document"),
                target: "new",
            });
        }
        if (key === "documents" || key === "workflows") {
            return this.action.doAction("hrsd.action_hr_esign_document", {
                additionalContext: key === "workflows" ? { search_default_in_progress: 1 } : {},
            });
        }
        if (key === "templates") {
            return this.action.doAction("hrsd.action_hr_esign_template");
        }
        if (key === "audit") {
            return this.action.doAction("hrsd.action_hr_esign_audit_log");
        }
        this.notification.add(_t("This workspace is coming soon."), { type: "info" });
    }

    onCustomize() {
        this.notification.add(_t("Dashboard customization is coming soon."), { type: "info" });
    }

    onViewAllDocuments() {
        this.action.doAction("hrsd.action_hr_esign_document");
    }

    onViewAllActivity() {
        this.action.doAction("hrsd.action_hr_esign_audit_log");
    }

    onOpenDocument(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.esign.document",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("hr_esign_dashboard", HrEsignDashboard);
