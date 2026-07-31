import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const STRIP_HTML = /<[^>]*>/g;
const RECORD_FIELDS = [
    "display_name", "employee_id", "email", "job_id", "department_id", "manager_id", "successor_id",
    "hr_user_id", "resignation_date", "last_working_day", "notice_period_days", "reason",
    "countdown", "progress", "priority", "kanban_state", "stage_id",
];

export class HrOffboardingJourney extends Component {
    static template = "hr_offboarding.EmployeeJourney";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.requestId = this.props.action.params && this.props.action.params.request_id;
        this.state = useState({
            record: null,
            stages: [],
            stageDates: {},
            tasks: [],
            clearances: [],
            assets: [],
            documents: [],
            payrolls: [],
            messages: [],
            expandedStageId: null,
            loading: true,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        if (!this.requestId) return;
        const [record] = await this.orm.read("hr.offboarding.request", [this.requestId], RECORD_FIELDS);
        this.state.record = record;

        this.state.stages = await this.orm.searchRead(
            "hr.offboarding.stage", [],
            ["name", "color", "is_final", "has_clearance", "has_assets", "has_documents", "has_payroll"],
            { order: "sequence" }
        );

        const logs = await this.orm.searchRead(
            "hr.offboarding.stage.log",
            [["request_id", "=", this.requestId]],
            ["stage_id", "date_entered"],
            { order: "date_entered" }
        );
        const stageDates = {};
        logs.forEach((log) => { stageDates[log.stage_id[0]] = log.date_entered; });
        this.state.stageDates = stageDates;
        this.state.expandedStageId = record.stage_id ? record.stage_id[0] : null;

        this.state.tasks = await this.orm.searchRead(
            "hr.offboarding.task",
            [["request_id", "=", this.requestId]],
            ["name", "stage_id", "assigned_to", "due_date", "done"],
            { order: "sequence" }
        );
        this.state.clearances = await this.orm.searchRead(
            "hr.offboarding.clearance",
            [["request_id", "=", this.requestId]],
            ["department", "status", "approver_id"]
        );
        this.state.assets = await this.orm.searchRead(
            "hr.offboarding.asset",
            [["request_id", "=", this.requestId]],
            ["name", "asset_type", "status"]
        );
        this.state.documents = await this.orm.searchRead(
            "hr.offboarding.document",
            [["request_id", "=", this.requestId]],
            ["name", "document_type", "status"]
        );
        this.state.payrolls = await this.orm.searchRead(
            "hr.offboarding.payroll",
            [["request_id", "=", this.requestId]],
            ["total_earnings", "total_deductions", "net_settlement", "status"]
        );

        const messages = await this.orm.searchRead(
            "mail.message",
            [["model", "=", "hr.offboarding.request"], ["res_id", "=", this.requestId]],
            ["body", "date", "author_id"],
            { limit: 15, order: "id desc" }
        );
        this.state.messages = messages
            .map((m) => ({ ...m, preview: (m.body || "").replace(STRIP_HTML, " ").trim() }))
            .filter((m) => m.preview);

        this.state.loading = false;
    }

    get stageIndex() {
        if (!this.state.record || !this.state.record.stage_id) return -1;
        return this.state.stages.findIndex((s) => s.id === this.state.record.stage_id[0]);
    }

    stageStatus(index) {
        const current = this.stageIndex;
        if (index < current) return "done";
        if (index === current) return "current";
        return "upcoming";
    }

    tasksForStage(stageId) {
        return this.state.tasks.filter((t) => t.stage_id && t.stage_id[0] === stageId);
    }

    get missingClearances() {
        return this.state.clearances.filter((c) => c.status === "pending" || c.status === "needs_action");
    }

    get missingAssets() {
        return this.state.assets.filter((a) => a.status === "pending");
    }

    get pendingTasks() {
        return this.state.tasks.filter((t) => !t.done);
    }

    toggleStage(stageId) {
        this.state.expandedStageId = this.state.expandedStageId === stageId ? null : stageId;
    }

    async toggleTask(task) {
        await this.orm.write("hr.offboarding.task", [task.id], { done: !task.done });
        task.done = !task.done;
    }

    async markStageComplete() {
        await this.orm.call("hr.offboarding.request", "action_move_next_stage", [[this.requestId]]);
        await this.loadData();
    }

    backToPipeline() {
        this.action.doAction("hr_offboarding.action_hr_offboarding_pipeline");
    }

    initials(name) {
        return (name || "?").trim().slice(0, 1).toUpperCase();
    }
}

registry.category("actions").add("hr_offboarding_journey", HrOffboardingJourney);
