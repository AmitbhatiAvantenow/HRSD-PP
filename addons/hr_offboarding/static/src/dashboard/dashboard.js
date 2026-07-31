import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const STRIP_HTML = /<[^>]*>/g;

export class HrOffboardingDashboard extends Component {
    static template = "hr_offboarding.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            kpis: {},
            todaysExits: [],
            recentActivity: [],
            pendingTasks: [],
            loading: true,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        const requests = await this.orm.searchRead(
            "hr.offboarding.request",
            [],
            [
                "display_name", "employee_id", "job_id", "department_id", "stage_id", "last_working_day",
                "progress", "countdown", "is_delayed", "asset_pending_count", "clearance_pending_count",
                "task_count", "task_done_count", "create_date", "write_date",
            ]
        );

        const payrolls = await this.orm.searchRead(
            "hr.offboarding.payroll", [["status", "!=", "paid"]], ["id"]
        );

        const todayStr = new Date().toISOString().slice(0, 10);
        const nameById = {};
        requests.forEach((r) => { nameById[r.id] = r.employee_id ? r.employee_id[1] : r.display_name; });

        let pendingAssets = 0, pendingClearances = 0, pendingTasksCount = 0;
        let completed = 0, delayed = 0, todaysExits = 0;

        for (const r of requests) {
            pendingAssets += r.asset_pending_count;
            pendingClearances += r.clearance_pending_count;
            pendingTasksCount += (r.task_count - r.task_done_count);
            if (r.is_delayed) delayed++;
            if (r.last_working_day === todayStr) todaysExits++;
            if (r.progress === 100) completed++;
        }

        this.state.kpis = {
            employeesLeaving: requests.length,
            todaysExits,
            pendingClearances,
            pendingAssets,
            payrollPending: payrolls.length,
            pendingTasks: pendingTasksCount,
            delayedOffboarding: delayed,
            completedOffboarding: completed,
        };

        this.state.todaysExits = requests.filter((r) => r.last_working_day === todayStr);

        const messages = await this.orm.searchRead(
            "mail.message",
            [["model", "=", "hr.offboarding.request"], ["res_id", "in", requests.map((r) => r.id)]],
            ["res_id", "body", "date", "author_id"],
            { limit: 8, order: "id desc" }
        );
        this.state.recentActivity = messages.map((m) => ({
            ...m,
            preview: (m.body || "").replace(STRIP_HTML, " ").trim().slice(0, 140),
            requestName: nameById[m.res_id] || "",
        })).filter((m) => m.preview);

        this.state.pendingTasks = await this.orm.searchRead(
            "hr.offboarding.task",
            [["done", "=", false]],
            ["name", "due_date", "request_id"],
            { limit: 6, order: "due_date" }
        );

        this.state.loading = false;
    }

    get kpiCards() {
        const k = this.state.kpis;
        return [
            { key: "employeesLeaving", label: "Employees Leaving", value: k.employeesLeaving, icon: "fa-sign-out", color: "red" },
            { key: "todaysExits", label: "Today's Exits", value: k.todaysExits, icon: "fa-calendar-check-o", color: "cyan" },
            { key: "pendingClearances", label: "Pending Approvals", value: k.pendingClearances, icon: "fa-check-square-o", color: "amber" },
            { key: "pendingAssets", label: "Pending Asset Returns", value: k.pendingAssets, icon: "fa-laptop", color: "amber" },
            { key: "payrollPending", label: "Payroll Pending", value: k.payrollPending, icon: "fa-money", color: "amber" },
            { key: "pendingTasks", label: "Pending Tasks", value: k.pendingTasks, icon: "fa-list-alt", color: "cyan" },
            { key: "delayedOffboarding", label: "Delayed Offboarding", value: k.delayedOffboarding, icon: "fa-exclamation-triangle", color: "red" },
            { key: "completedOffboarding", label: "Completed Offboarding", value: k.completedOffboarding, icon: "fa-trophy", color: "green" },
        ];
    }

    openAction(xmlId) {
        this.action.doAction(xmlId);
    }

    openNewRequest() {
        this.action.doAction("hr_offboarding.action_hr_offboarding_request_new");
    }
}

registry.category("actions").add("hr_offboarding_dashboard", HrOffboardingDashboard);
