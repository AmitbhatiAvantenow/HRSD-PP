import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const STRIP_HTML = /<[^>]*>/g;

export class HrOnboardingDashboard extends Component {
    static template = "hr_onboarding.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            kpis: {},
            todaysJoiners: [],
            recentActivity: [],
            pendingTasks: [],
            loading: true,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        const onboardings = await this.orm.searchRead(
            "hr.onboarding",
            [],
            [
                "display_name", "job_id", "department_id", "stage_id", "joining_date",
                "progress", "countdown", "is_delayed", "missing_document_count",
                "equipment_pending_count", "task_count", "task_done_count",
                "create_date", "write_date",
            ]
        );

        const todayStr = new Date().toISOString().slice(0, 10);
        const nameById = {};
        onboardings.forEach((o) => { nameById[o.id] = o.display_name; });

        let pendingDocuments = 0, equipmentPending = 0, pendingTasksCount = 0;
        let completed = 0, delayed = 0, joiningToday = 0;
        let completionDaysTotal = 0, completionCount = 0;

        for (const o of onboardings) {
            pendingDocuments += o.missing_document_count;
            equipmentPending += o.equipment_pending_count;
            pendingTasksCount += (o.task_count - o.task_done_count);
            if (o.is_delayed) delayed++;
            if (o.joining_date === todayStr) joiningToday++;
            if (o.progress === 100) {
                completed++;
                const days = (new Date(o.write_date) - new Date(o.create_date)) / 86400000;
                completionDaysTotal += days;
                completionCount++;
            }
        }

        this.state.kpis = {
            newHires: onboardings.length,
            joiningToday,
            pendingDocuments,
            equipmentPending,
            completedJourney: completed,
            delayedOnboarding: delayed,
            pendingTasks: pendingTasksCount,
            avgCompletionDays: completionCount ? Math.round(completionDaysTotal / completionCount) : 0,
        };

        this.state.todaysJoiners = onboardings.filter((o) => o.joining_date === todayStr);

        const messages = await this.orm.searchRead(
            "mail.message",
            [["model", "=", "hr.onboarding"], ["res_id", "in", onboardings.map((o) => o.id)]],
            ["res_id", "body", "date", "author_id"],
            { limit: 8, order: "id desc" }
        );
        this.state.recentActivity = messages.map((m) => ({
            ...m,
            preview: (m.body || "").replace(STRIP_HTML, " ").trim().slice(0, 140),
            onboardingName: nameById[m.res_id] || "",
        })).filter((m) => m.preview);

        this.state.pendingTasks = await this.orm.searchRead(
            "hr.onboarding.task",
            [["done", "=", false]],
            ["name", "due_date", "onboarding_id"],
            { limit: 6, order: "due_date" }
        );

        this.state.loading = false;
    }

    get kpiCards() {
        const k = this.state.kpis;
        return [
            { key: "newHires", label: "New Hires", value: k.newHires, icon: "fa-user-plus", color: "indigo" },
            { key: "joiningToday", label: "Joining Today", value: k.joiningToday, icon: "fa-calendar-check-o", color: "cyan" },
            { key: "pendingDocuments", label: "Pending Documents", value: k.pendingDocuments, icon: "fa-file-text-o", color: "amber" },
            { key: "equipmentPending", label: "Equipment Pending", value: k.equipmentPending, icon: "fa-laptop", color: "amber" },
            { key: "pendingTasks", label: "Pending Tasks", value: k.pendingTasks, icon: "fa-check-square-o", color: "cyan" },
            { key: "delayedOnboarding", label: "Delayed Onboarding", value: k.delayedOnboarding, icon: "fa-exclamation-triangle", color: "red" },
            { key: "completedJourney", label: "Completed Journeys", value: k.completedJourney, icon: "fa-trophy", color: "green" },
            { key: "avgCompletionDays", label: "Avg. Completion (days)", value: k.avgCompletionDays, icon: "fa-line-chart", color: "indigo" },
        ];
    }

    openAction(xmlId) {
        this.action.doAction(xmlId);
    }

    openNewOnboarding() {
        this.action.doAction("hr_onboarding.action_hr_onboarding_new");
    }
}

registry.category("actions").add("hr_onboarding_dashboard", HrOnboardingDashboard);
