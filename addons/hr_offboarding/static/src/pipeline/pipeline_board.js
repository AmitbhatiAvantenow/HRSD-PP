import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable_owl";
import { Component, onWillStart, useRef, useState } from "@odoo/owl";

const PRIORITY_LABELS = { "0": "Low", "1": "Normal", "2": "High", "3": "Urgent" };
const FIELDS = [
    "display_name", "employee_id", "job_id", "department_id", "manager_id", "hr_user_id",
    "last_working_day", "progress", "countdown", "is_delayed", "priority", "stage_id", "kanban_state",
];

export class HrOffboardingPipeline extends Component {
    static template = "hr_offboarding.PipelineBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.state = useState({ columns: [], loading: true });

        onWillStart(() => this.loadData());

        let sourceStageId = null;
        useSortable({
            ref: this.rootRef,
            elements: ".hro-pipe-card",
            ignore: "button, .hro-pipe-card-action",
            groups: ".hro-pipe-col-body",
            connectGroups: true,
            cursor: "grabbing",
            placeholderClasses: ["hro-pipe-placeholder"],
            onDragStart: ({ element }) => {
                const col = element.closest(".hro-pipe-col-body");
                sourceStageId = col && parseInt(col.dataset.stageId);
            },
            onDrop: ({ element, parent }) => {
                const recordId = parseInt(element.dataset.id);
                const targetStageId = parent && parseInt(parent.dataset.stageId);
                if (targetStageId && recordId && targetStageId !== sourceStageId) {
                    this.moveRecord(recordId, sourceStageId, targetStageId);
                }
            },
        });
    }

    async loadData() {
        const stages = await this.orm.searchRead(
            "hr.offboarding.stage",
            [],
            ["name", "color", "fold", "is_final"],
            { order: "sequence" }
        );
        const records = await this.orm.searchRead("hr.offboarding.request", [], FIELDS);

        this.state.columns = stages.map((stage) => ({
            stage,
            records: records.filter((r) => r.stage_id && r.stage_id[0] === stage.id),
        }));
        this.state.loading = false;
    }

    async moveRecord(recordId, sourceStageId, targetStageId) {
        const sourceCol = this.state.columns.find((c) => c.stage.id === sourceStageId);
        const targetCol = this.state.columns.find((c) => c.stage.id === targetStageId);
        if (!sourceCol || !targetCol) return;
        const idx = sourceCol.records.findIndex((r) => r.id === recordId);
        if (idx === -1) return;
        const [record] = sourceCol.records.splice(idx, 1);
        record.stage_id = [targetCol.stage.id, targetCol.stage.name];
        record.progress = targetCol.stage.is_final ? 100 : record.progress;
        targetCol.records.unshift(record);
        await this.orm.write("hr.offboarding.request", [recordId], { stage_id: targetStageId });
    }

    priorityLabel(priority) {
        return PRIORITY_LABELS[priority] || "Normal";
    }

    openJourney(recordId) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "hr_offboarding_journey",
            params: { request_id: recordId },
        });
    }

    openNewRequest() {
        this.action.doAction("hr_offboarding.action_hr_offboarding_request_new");
    }

    initials(name) {
        return (name || "?").trim().slice(0, 1).toUpperCase();
    }
}

registry.category("actions").add("hr_offboarding_pipeline", HrOffboardingPipeline);
