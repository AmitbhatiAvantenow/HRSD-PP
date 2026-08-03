import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";

const RING_COLORS = ["--doc-primary", "--doc-info", "--doc-success", "--doc-warning", "--doc-purple", "--doc-danger"];

export class Dashboard extends Component {
    static template = "document_templates.Dashboard";
    static components = { DocShell };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            stats: {
                total_templates: 0, generated_this_month: 0, shared_templates: 0,
                favourite_templates: 0,
            },
            most_used: [],
            by_department: [],
            generated_trend: [],
            category_breakdown: [],
            recently_modified: [],
        });

        onWillStart(async () => {
            const data = await this.orm.call("document.template", "get_dashboard_data", []);
            Object.assign(this.state, data);
        });
    }

    get maxUsage() {
        return Math.max(...this.state.most_used.map((t) => t.usage_count), 1);
    }

    get maxDeptCount() {
        return Math.max(...this.state.by_department.map((d) => d.count), 1);
    }

    get maxTrendCount() {
        return Math.max(...this.state.generated_trend.map((t) => t.count), 1);
    }

    get categoryRingStyle() {
        const cats = this.state.category_breakdown;
        if (!cats.length) return "";
        const stops = cats.map((c, i) => {
            const color = `var(${RING_COLORS[i % RING_COLORS.length]})`;
            return `${color} ${c.cumulative_pct}% ${c.cumulative_pct + c.pct}%`;
        });
        return `background: conic-gradient(${stops.join(", ")});`;
    }

    categoryDotColor(index) {
        return RING_COLORS[index % RING_COLORS.length];
    }

    openTemplates() {
        this.action.doAction("document_templates.action_doc_templates");
    }
}

registry.category("actions").add("doc_dashboard", Dashboard);
