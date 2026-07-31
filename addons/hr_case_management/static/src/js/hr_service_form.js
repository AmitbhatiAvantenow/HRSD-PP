/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

/**
 * Backend client action: renders a Form Template (hr.case.producer) as a
 * ServiceNow-style self-service form within the Odoo dashboard.
 *
 * Triggered by:
 *   - "Submit Request" button on the Service Catalog kanban card
 *   - Direct URL:  /odoo/action-hr_case_management.action_hr_case_service_form
 *                  (with context.producer_id set)
 */
export class HrServiceForm extends Component {
    static template = "hr_case_management.ServiceForm";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            fatalError: null,
            producer: null,
            questions: [],
            allEmployees: [],
            employee: null,
            shortDescription: "",
            answers: {},
            submitting: false,
            error: null,
        });

        onWillStart(async () => {
            const producerId =
                this.props.action?.context?.producer_id ||
                this.props.context?.producer_id;

            if (!producerId) {
                this.state.loading = false;
                this.state.fatalError =
                    "No form template specified. Please open this page via the Service Catalog.";
                return;
            }

            try {
                // ── Load producer ──────────────────────────────────────────
                const [producer] = await this.orm.read(
                    "hr.case.producer",
                    [producerId],
                    ["name", "description", "service_id", "question_ids"]
                );

                // ── Load questions ─────────────────────────────────────────
                let questions = [];
                if (producer.question_ids.length) {
                    questions = await this.orm.read(
                        "hr.case.producer.question",
                        producer.question_ids,
                        [
                            "label", "field_type", "required",
                            "help_text", "placeholder",
                            "selection_values", "map_to_field", "sequence",
                        ]
                    );
                    questions.sort((a, b) => a.sequence - b.sequence);
                }

                // ── All employees (for employee-type questions) ────────────
                const allEmployees = await this.orm.searchRead(
                    "hr.employee",
                    [["active", "=", true]],
                    ["id", "name"],
                    { order: "name asc" }
                );

                // ── Current user's employee profile ────────────────────────
                const employees = await this.orm.searchRead(
                    "hr.employee",
                    [["user_id", "=", user.userId]],
                    ["id", "name"],
                    { limit: 1 }
                );

                // ── Initialise blank answers ───────────────────────────────
                const answers = {};
                for (const q of questions) {
                    answers[q.id] = q.field_type === "boolean" ? false : "";
                }

                Object.assign(this.state, {
                    loading: false,
                    producer,
                    questions,
                    allEmployees,
                    employee: employees[0] || null,
                    answers,
                });
            } catch (e) {
                this.state.loading = false;
                this.state.fatalError =
                    "Failed to load the form. " + (e.data?.message || e.message || "");
            }
        });
    }

    // ── Helpers ─────────────────────────────────────────────────────────────

    getColClass(q) {
        return ["textarea", "employee"].includes(q.field_type)
            ? "col-12"
            : "col-12 col-md-6";
    }

    getSelectionOptions(q) {
        return (q.selection_values || "")
            .trim()
            .split("\n")
            .map((o) => o.trim())
            .filter(Boolean);
    }

    updateAnswer(questionId, value) {
        this.state.answers[questionId] = value;
    }

    // ── Submit ───────────────────────────────────────────────────────────────

    async onSubmit() {
        if (this.state.submitting) return;
        this.state.error = null;

        // Client-side validation
        const subject = this.state.shortDescription.trim();
        if (!subject) {
            this.state.error = "Please enter a Subject / Summary.";
            return;
        }

        for (const q of this.state.questions) {
            if (!q.required) continue;
            if (q.field_type === "boolean") continue; // always has a value
            if (!this.state.answers[q.id]) {
                this.state.error = `Please answer the required question: "${q.label}"`;
                return;
            }
        }

        this.state.submitting = true;
        try {
            // 1. Create submission record
            const [submissionId] = await this.orm.create("hr.case.submission", [
                {
                    producer_id: this.state.producer.id,
                    employee_id: this.state.employee?.id || false,
                    short_description: subject,
                },
            ]);

            // 2. Create answer records
            for (const q of this.state.questions) {
                const raw = this.state.answers[q.id];
                const vals = {
                    submission_id: submissionId,
                    question_id: q.id,
                };
                if (q.field_type === "text")          vals.value_char = raw || "";
                else if (q.field_type === "textarea")  vals.value_text = raw || "";
                else if (q.field_type === "date")      vals.value_date = raw || false;
                else if (q.field_type === "boolean")   vals.value_boolean = raw;
                else if (q.field_type === "employee")  vals.value_employee_id = raw || false;
                else if (q.field_type === "selection") vals.value_selection = raw || "";
                await this.orm.create("hr.case.submission.answer", [vals]);
            }

            // 3. Call action_submit — creates hr.case and marks submission submitted
            await this.orm.call("hr.case.submission", "action_submit", [[submissionId]]);

            // 4. Read back the created case id
            const [submission] = await this.orm.read(
                "hr.case.submission",
                [submissionId],
                ["case_id"]
            );

            this.notification.add("Request submitted successfully!", {
                type: "success",
            });

            // 5. Navigate to the new HR Case in the backend
            if (submission.case_id) {
                await this.actionService.doAction({
                    type: "ir.actions.act_window",
                    name: "HR Case",
                    res_model: "hr.case",
                    res_id: submission.case_id[0],
                    views: [[false, "form"]],
                    target: "current",
                });
            } else {
                this.actionService.doAction(-1);
            }
        } catch (e) {
            this.state.error =
                e.data?.message || e.message || "An unexpected error occurred.";
        } finally {
            this.state.submitting = false;
        }
    }

    onCancel() {
        this.actionService.doAction(-1);
    }
}

registry.category("actions").add("hr_case.service_form", HrServiceForm);
