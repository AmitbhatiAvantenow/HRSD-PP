/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { Many2One } from "@web/views/fields/many2one/many2one";

function toDateStr(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

function mondayOf(date) {
    const d = new Date(date);
    const dow = d.getDay();
    const diff = (dow === 0 ? -6 : 1) - dow;
    d.setDate(d.getDate() + diff);
    d.setHours(0, 0, 0, 0);
    return d;
}

function toTimeInput(value) {
    if (value === undefined || value === null || isNaN(value)) value = 0;
    const h = Math.floor(value);
    const m = Math.round((value - h) * 60);
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function fromTimeInput(str) {
    if (!str) return 0;
    const [h, m] = str.split(":").map(Number);
    return (h || 0) + (m || 0) / 60;
}

export class HrTimesheetProLogTimeWizard extends Component {
    static template = "hr_timesheet_pro.LogTimeWizard";
    static components = { Many2One };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.toTimeInput = toTimeInput;

        const today = new Date();

        this.state = useState({
            loadingEmployee: true,
            checkingWeek: false,
            employeeId: false,
            employeeName: "",
            date: toDateStr(today),
            projectId: false,
            projectName: "",
            taskId: false,
            taskName: "",
            start: 9,
            end: 17,
            hours: 8,
            billable: true,
            comments: "",
            sheetId: false,
            sheetName: "",
            sheetState: false,
            locked: false,
            existingLineId: false,
            saving: false,
            success: false,
            error: "",
        });

        onWillStart(async () => {
            const employees = await this.orm.searchRead(
                "hr.employee",
                [["user_id", "=", user.userId]],
                ["id", "name"],
                { limit: 1 }
            );
            const employee = employees[0];
            if (!employee) {
                this.state.error = _t("No employee record is linked to your user account.");
                this.state.loadingEmployee = false;
                return;
            }
            this.state.employeeId = employee.id;
            this.state.employeeName = employee.name;
            this.state.loadingEmployee = false;
            await this.checkWeek();
        });
    }

    // -------------------------------------------------------------------
    get avatarUrl() {
        return this.state.employeeId
            ? `/web/image/hr.employee/${this.state.employeeId}/avatar_128`
            : "";
    }
    get isCommentRequired() {
        return this.state.billable && this.state.hours > 0;
    }
    get isCommentMissing() {
        return this.isCommentRequired && !(this.state.comments && this.state.comments.trim());
    }
    get projectPickerProps() {
        return {
            relation: "project.project",
            value: this.state.projectId
                ? { id: this.state.projectId, display_name: this.state.projectName }
                : false,
            update: (v) => {
                this.state.projectId = v ? v.id : false;
                this.state.projectName = v ? v.display_name : "";
                if (!v) {
                    this.state.taskId = false;
                    this.state.taskName = "";
                }
            },
            domain: () => [],
            placeholder: _t("Search or select a project…"),
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            canOpen: true,
        };
    }
    get taskPickerProps() {
        return {
            relation: "project.task",
            value: this.state.taskId
                ? { id: this.state.taskId, display_name: this.state.taskName }
                : false,
            update: (v) => {
                this.state.taskId = v ? v.id : false;
                this.state.taskName = v ? v.display_name : "";
            },
            domain: () => (this.state.projectId ? [["project_id", "=", this.state.projectId]] : []),
            placeholder: _t("Search or select a task…"),
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            canOpen: true,
        };
    }

    // -------------------------------------------------------------------
    // Week / existing entry lookup — Log Time always upserts into the
    // Monday-Sunday sheet that owns the chosen date, same as the weekly
    // wizard, so the two flows never create conflicting records.
    // -------------------------------------------------------------------
    async checkWeek() {
        this.state.checkingWeek = true;
        this.state.error = "";
        try {
            const monday = mondayOf(new Date(this.state.date + "T00:00:00"));
            const mondayStr = toDateStr(monday);
            const sheets = await this.orm.searchRead(
                "hr.timesheet.sheet",
                [["employee_id", "=", this.state.employeeId], ["date_start", "=", mondayStr]],
                ["id", "name", "state", "project_id"],
                { limit: 1 }
            );
            const sheet = sheets[0];
            if (!sheet) {
                this.state.sheetId = false;
                this.state.sheetName = "";
                this.state.sheetState = false;
                this.state.locked = false;
                this.state.existingLineId = false;
                return;
            }
            this.state.sheetId = sheet.id;
            this.state.sheetName = sheet.name;
            this.state.sheetState = sheet.state;
            this.state.locked = !["draft", "returned"].includes(sheet.state);
            if (!this.state.projectId && sheet.project_id) {
                this.state.projectId = sheet.project_id[0];
                this.state.projectName = sheet.project_id[1];
            }
            if (this.state.locked) {
                this.state.existingLineId = false;
                return;
            }
            const lines = await this.orm.searchRead(
                "hr.timesheet.line",
                [["sheet_id", "=", sheet.id], ["date", "=", this.state.date]],
                ["id", "start_time", "end_time", "hours", "billable", "comments", "task_id"],
                { limit: 1 }
            );
            const line = lines[0];
            if (line) {
                this.state.existingLineId = line.id;
                this.state.start = line.start_time;
                this.state.end = line.end_time;
                this.state.hours = line.hours;
                this.state.billable = line.billable;
                this.state.comments = line.comments || "";
                this.state.taskId = line.task_id ? line.task_id[0] : false;
                this.state.taskName = line.task_id ? line.task_id[1] : "";
            } else {
                this.state.existingLineId = false;
            }
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.checkingWeek = false;
        }
    }

    async onDateChange(ev) {
        this.state.date = ev.target.value;
        await this.checkWeek();
    }

    recomputeHours() {
        const h = this.state.end - this.state.start;
        this.state.hours = Math.round(Math.max(0, h) * 100) / 100;
    }
    onStartChange(ev) {
        this.state.start = fromTimeInput(ev.target.value);
        this.recomputeHours();
    }
    onEndChange(ev) {
        this.state.end = fromTimeInput(ev.target.value);
        this.recomputeHours();
    }
    toggleBillable() {
        this.state.billable = !this.state.billable;
    }

    _errorMessage(e) {
        return (e && e.data && e.data.message) || (e && e.message) || _t("Something went wrong.");
    }

    async onSave() {
        if (this.state.locked) return;
        this.state.error = "";
        this.state.saving = true;
        try {
            const lineVals = {
                date: this.state.date,
                start_time: this.state.start,
                end_time: this.state.end,
                hours: this.state.hours,
                billable: this.state.billable,
                comments: this.state.comments || false,
                task_id: this.state.taskId || false,
            };
            let sheetId = this.state.sheetId;
            if (!sheetId) {
                const monday = mondayOf(new Date(this.state.date + "T00:00:00"));
                const ids = await this.orm.create("hr.timesheet.sheet", [{
                    employee_id: this.state.employeeId,
                    date_start: toDateStr(monday),
                    project_id: this.state.projectId || false,
                    line_ids: [[0, 0, lineVals]],
                }]);
                sheetId = ids[0];
                this.state.sheetId = sheetId;
            } else {
                await this.orm.write("hr.timesheet.sheet", [sheetId], {
                    project_id: this.state.projectId || false,
                });
                if (this.state.existingLineId) {
                    await this.orm.write("hr.timesheet.line", [this.state.existingLineId], lineVals);
                } else {
                    const lineIds = await this.orm.create("hr.timesheet.line", [{
                        ...lineVals,
                        sheet_id: sheetId,
                    }]);
                    this.state.existingLineId = lineIds[0];
                }
            }
            this.state.success = true;
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.saving = false;
        }
    }

    logAnother() {
        const today = new Date();
        this.state.success = false;
        this.state.date = toDateStr(today);
        this.state.taskId = false;
        this.state.taskName = "";
        this.state.start = 9;
        this.state.end = 17;
        this.state.hours = 8;
        this.state.billable = true;
        this.state.comments = "";
        this.state.existingLineId = false;
        this.checkWeek();
    }

    viewTimesheet() {
        if (!this.state.sheetId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.timesheet.sheet",
            res_id: this.state.sheetId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openWeeklyWizard() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "hr_timesheet_pro_fill_wizard",
            name: _t("Submit Weekly Timesheet"),
            target: "new",
        });
    }

    onCancel() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
    onClose() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("hr_timesheet_pro_log_time_wizard", HrTimesheetProLogTimeWizard);
