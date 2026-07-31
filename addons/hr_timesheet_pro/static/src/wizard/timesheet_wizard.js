/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { Many2One } from "@web/views/fields/many2one/many2one";

const STEPS = [
    { key: "setup", label: _t("Week & Project"), icon: "fa-calendar" },
    { key: "log", label: _t("Daily Log"), icon: "fa-clock-o" },
    { key: "review", label: _t("Review & Submit"), icon: "fa-check" },
];

const DAY_FIELDS = ["date", "start_time", "end_time", "hours", "billable", "comments", "task_id"];

function toDateStr(d) {
    // Avoid toISOString(): it converts to UTC first, shifting the date
    // backward a day in timezones behind UTC.
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

export class HrTimesheetProFillWizard extends Component {
    static template = "hr_timesheet_pro.FillWizard";
    static components = { Many2One };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.steps = STEPS;
        this.toTimeInput = toTimeInput;

        this.state = useState({
            step: 0,
            loadingEmployee: true,
            loadingWeek: true,
            copying: false,
            employeeId: false,
            employeeName: "",
            weekStartStr: toDateStr(mondayOf(new Date())),
            sheetId: false,
            sheetName: "",
            sheetState: false,
            locked: false,
            projectId: false,
            projectName: "",
            targetHours: 40,
            days: [],
            submitting: false,
            savingDraft: false,
            error: "",
            success: false,
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
            await this.loadWeek(this.weekStartDate);
        });
    }

    // -------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------
    get currentStep() {
        return this.state.success ? "success" : this.steps[this.state.step].key;
    }
    get isFirstStep() { return this.state.step === 0; }
    get isLastStep() { return this.state.step === this.steps.length - 1; }
    get progressPct() {
        if (this.state.success) return 100;
        return Math.round(((this.state.step + 1) / this.steps.length) * 100);
    }
    get weekStartDate() {
        return new Date(this.state.weekStartStr + "T00:00:00");
    }
    get weekEnd() {
        const d = this.weekStartDate;
        d.setDate(d.getDate() + 6);
        return d;
    }
    get weekStartYear() {
        return this.weekStartDate.getFullYear();
    }
    get weekLabel() {
        const opts = { month: "short", day: "numeric" };
        return `${this.weekStartDate.toLocaleDateString(undefined, opts)} – ${this.weekEnd.toLocaleDateString(undefined, opts)}`;
    }
    get totalHours() {
        return Math.round(this.state.days.reduce((s, d) => s + (d.hours || 0), 0) * 100) / 100;
    }
    get billableHours() {
        return Math.round(
            this.state.days.filter((d) => d.billable).reduce((s, d) => s + (d.hours || 0), 0) * 100
        ) / 100;
    }
    get progressHoursPct() {
        return Math.min(100, Math.round((this.totalHours / (this.state.targetHours || 40)) * 100));
    }
    get missingCommentDays() {
        return this.state.days.filter((d) => this.isCommentMissing(d));
    }
    get avatarUrl() {
        return this.state.employeeId
            ? `/web/image/hr.employee/${this.state.employeeId}/avatar_128`
            : "";
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
            },
            domain: () => [],
            placeholder: _t("Search or select a project…"),
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            canOpen: true,
        };
    }

    isCommentRequired(day) {
        return day.billable && day.hours > 0;
    }
    isCommentMissing(day) {
        return this.isCommentRequired(day) && !(day.comments && day.comments.trim());
    }

    // -------------------------------------------------------------------
    // Week loading
    // -------------------------------------------------------------------
    _buildDefaultDays(monday) {
        return Array.from({ length: 7 }, (_, i) => {
            const d = new Date(monday);
            d.setDate(monday.getDate() + i);
            const isWeekend = i >= 5;
            const todayStr = toDateStr(new Date());
            return {
                date: toDateStr(d),
                dayName: d.toLocaleDateString(undefined, { weekday: "long" }),
                shortDay: d.toLocaleDateString(undefined, { weekday: "short" }),
                start: 9,
                end: isWeekend ? 0 : 17,
                hours: isWeekend ? 0 : 8,
                billable: !isWeekend,
                comments: "",
                taskId: false,
                isWeekend,
                isToday: toDateStr(d) === todayStr,
            };
        });
    }

    _buildDaysFromLines(monday, lines) {
        const byDate = {};
        for (const l of lines) byDate[l.date] = l;
        return this._buildDefaultDays(monday).map((day) => {
            const line = byDate[day.date];
            if (!line) return day;
            return {
                ...day,
                lineId: line.id,
                start: line.start_time,
                end: line.end_time,
                hours: line.hours,
                billable: line.billable,
                comments: line.comments || "",
                taskId: line.task_id ? line.task_id[0] : false,
            };
        });
    }

    async loadWeek(monday) {
        this.state.loadingWeek = true;
        this.state.error = "";
        const mondayStr = toDateStr(monday);
        this.state.weekStartStr = mondayStr;
        try {
            const sheets = await this.orm.searchRead(
                "hr.timesheet.sheet",
                [["employee_id", "=", this.state.employeeId], ["date_start", "=", mondayStr]],
                ["id", "name", "state", "project_id", "target_hours"],
                { limit: 1 }
            );
            const sheet = sheets[0];
            if (sheet) {
                const lines = await this.orm.searchRead(
                    "hr.timesheet.line",
                    [["sheet_id", "=", sheet.id]],
                    DAY_FIELDS,
                    { order: "date" }
                );
                this.state.sheetId = sheet.id;
                this.state.sheetName = sheet.name;
                this.state.sheetState = sheet.state;
                this.state.locked = !["draft", "returned"].includes(sheet.state);
                this.state.projectId = sheet.project_id ? sheet.project_id[0] : false;
                this.state.projectName = sheet.project_id ? sheet.project_id[1] : "";
                this.state.targetHours = sheet.target_hours || 40;
                this.state.days = this._buildDaysFromLines(monday, lines);
            } else {
                this.state.sheetId = false;
                this.state.sheetName = "";
                this.state.sheetState = false;
                this.state.locked = false;
                this.state.days = this._buildDefaultDays(monday);
            }
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingWeek = false;
        }
    }

    async goPrevWeek() {
        const m = this.weekStartDate;
        m.setDate(m.getDate() - 7);
        await this.loadWeek(m);
    }
    async goNextWeek() {
        const m = this.weekStartDate;
        m.setDate(m.getDate() + 7);
        await this.loadWeek(m);
    }

    async copyLastWeek() {
        this.state.copying = true;
        this.state.error = "";
        try {
            const prevMonday = this.weekStartDate;
            prevMonday.setDate(prevMonday.getDate() - 7);
            const prevSunday = new Date(prevMonday);
            prevSunday.setDate(prevSunday.getDate() + 6);
            const lines = await this.orm.searchRead(
                "hr.timesheet.line",
                [
                    ["employee_id", "=", this.state.employeeId],
                    ["date", ">=", toDateStr(prevMonday)],
                    ["date", "<=", toDateStr(prevSunday)],
                ],
                DAY_FIELDS,
                { order: "date" }
            );
            if (!lines.length) {
                this.notification.add(_t("No timesheet found for the previous week."), { type: "warning" });
                return;
            }
            const byWeekday = {};
            for (const l of lines) {
                const wd = new Date(l.date + "T00:00:00").getDay();
                byWeekday[wd === 0 ? 6 : wd - 1] = l;
            }
            this.state.days.forEach((day, i) => {
                const l = byWeekday[i];
                if (!l) return;
                day.start = l.start_time;
                day.end = l.end_time;
                day.hours = l.hours;
                day.billable = l.billable;
                day.comments = l.comments || "";
                day.taskId = l.task_id ? l.task_id[0] : false;
            });
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.copying = false;
        }
    }

    // -------------------------------------------------------------------
    // Daily log interactions
    // -------------------------------------------------------------------
    recomputeHours(day) {
        const h = day.end - day.start;
        day.hours = Math.round(Math.max(0, h) * 100) / 100;
    }
    onStartChange(day, ev) {
        day.start = fromTimeInput(ev.target.value);
        this.recomputeHours(day);
    }
    onEndChange(day, ev) {
        day.end = fromTimeInput(ev.target.value);
        this.recomputeHours(day);
    }
    onCommentsChange(day, ev) {
        day.comments = ev.target.value;
    }
    toggleBillable(day) {
        day.billable = !day.billable;
    }

    // -------------------------------------------------------------------
    // Navigation
    // -------------------------------------------------------------------
    canProceed() {
        if (this.state.step === 0) return !this.state.locked;
        return true;
    }
    goNext() {
        if (!this.canProceed()) return;
        this.state.error = "";
        if (!this.isLastStep) this.state.step++;
    }
    goBack() {
        this.state.error = "";
        if (!this.isFirstStep) this.state.step--;
    }
    goToStep(index) {
        if (this.state.success || index > this.state.step) return;
        this.state.step = index;
    }

    // -------------------------------------------------------------------
    // Persistence
    // -------------------------------------------------------------------
    _errorMessage(e) {
        return (e && e.data && e.data.message) || (e && e.message) || _t("Something went wrong.");
    }

    async _persist() {
        const lineCommands = this.state.days.map((d) => [0, 0, {
            date: d.date,
            start_time: d.start,
            end_time: d.end,
            hours: d.hours,
            billable: d.billable,
            comments: d.comments || false,
            task_id: d.taskId || false,
        }]);
        if (this.state.sheetId) {
            await this.orm.write("hr.timesheet.sheet", [this.state.sheetId], {
                project_id: this.state.projectId || false,
                line_ids: [[5, 0, 0], ...lineCommands],
            });
            return this.state.sheetId;
        }
        const ids = await this.orm.create("hr.timesheet.sheet", [{
            employee_id: this.state.employeeId,
            date_start: this.state.weekStartStr,
            project_id: this.state.projectId || false,
            line_ids: lineCommands,
        }]);
        this.state.sheetId = ids[0];
        return ids[0];
    }

    async onSaveDraft() {
        this.state.savingDraft = true;
        this.state.error = "";
        try {
            const id = await this._persist();
            this.notification.add(_t("Draft saved."), { type: "success" });
            this._openRecord(id);
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.savingDraft = false;
        }
    }

    async onSubmit() {
        if (this.missingCommentDays.length) {
            this.state.error = _t(
                "Comments are mandatory for billable days: %s",
                this.missingCommentDays.map((d) => d.dayName).join(", ")
            );
            this.state.step = 1;
            return;
        }
        this.state.submitting = true;
        this.state.error = "";
        try {
            const id = await this._persist();
            await this.orm.call("hr.timesheet.sheet", "action_submit", [[id]]);
            this.state.sheetState = "submitted";
            this.state.success = true;
        } catch (e) {
            this.state.error = this._errorMessage(e);
            this.state.step = 1;
        } finally {
            this.state.submitting = false;
        }
    }

    _openRecord(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.timesheet.sheet",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    viewTimesheet() {
        if (this.state.sheetId) this._openRecord(this.state.sheetId);
    }

    onCancel() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
    onClose() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("hr_timesheet_pro_fill_wizard", HrTimesheetProFillWizard);
