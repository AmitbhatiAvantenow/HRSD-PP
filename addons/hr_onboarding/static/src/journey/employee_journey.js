import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const STRIP_HTML = /<[^>]*>/g;
const RECORD_FIELDS = [
    "display_name", "first_name", "last_name", "email", "phone", "gender", "image_1920",
    "job_id", "department_id", "manager_id", "buddy_id", "hr_user_id", "joining_date",
    "countdown", "progress", "priority", "kanban_state", "stage_id",
];

export class HrOnboardingJourney extends Component {
    static template = "hr_onboarding.EmployeeJourney";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.onboardingId = this.props.action.params && this.props.action.params.onboarding_id;
        this.state = useState({
            record: null,
            stages: [],
            stageDates: {},
            tasks: [],
            documents: [],
            messages: [],
            expandedStageId: null,
            loading: true,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        if (!this.onboardingId) return;
        const [record] = await this.orm.read("hr.onboarding", [this.onboardingId], RECORD_FIELDS);
        this.state.record = record;

        this.state.stages = await this.orm.searchRead(
            "hr.onboarding.stage", [], ["name", "color", "is_final", "has_documents"], { order: "sequence" }
        );

        const logs = await this.orm.searchRead(
            "hr.onboarding.stage.log",
            [["onboarding_id", "=", this.onboardingId]],
            ["stage_id", "date_entered"],
            { order: "date_entered" }
        );
        const stageDates = {};
        logs.forEach((log) => { stageDates[log.stage_id[0]] = log.date_entered; });
        this.state.stageDates = stageDates;
        this.state.expandedStageId = record.stage_id ? record.stage_id[0] : null;

        this.state.tasks = await this.orm.searchRead(
            "hr.onboarding.task",
            [["onboarding_id", "=", this.onboardingId]],
            ["name", "stage_id", "assigned_to", "due_date", "done"],
            { order: "sequence" }
        );
        this.state.documents = await this.orm.searchRead(
            "hr.onboarding.document",
            [["onboarding_id", "=", this.onboardingId]],
            ["name", "document_type", "status", "expiry_date"]
        );
        const messages = await this.orm.searchRead(
            "mail.message",
            [["model", "=", "hr.onboarding"], ["res_id", "=", this.onboardingId]],
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

    get missingDocuments() {
        return this.state.documents.filter((d) => d.status === "pending" || d.status === "rejected");
    }

    get pendingTasks() {
        return this.state.tasks.filter((t) => !t.done);
    }

    toggleStage(stageId) {
        this.state.expandedStageId = this.state.expandedStageId === stageId ? null : stageId;
    }

    async toggleTask(task) {
        await this.orm.write("hr.onboarding.task", [task.id], { done: !task.done });
        task.done = !task.done;
    }

    async markStageComplete() {
        await this.orm.call("hr.onboarding", "action_move_next_stage", [[this.onboardingId]]);
        await this.loadData();
    }

    async sendDocumentRequest() {
        await this.orm.call("hr.onboarding", "action_send_document_request", [[this.onboardingId]]);
        this.notification.add("Document request email sent.", { type: "success" });
        await this.loadData();
    }

    backToPipeline() {
        this.action.doAction("hr_onboarding.action_hr_onboarding_pipeline");
    }

    initials(name) {
        return (name || "?").trim().slice(0, 1).toUpperCase();
    }
}

registry.category("actions").add("hr_onboarding_journey", HrOnboardingJourney);
