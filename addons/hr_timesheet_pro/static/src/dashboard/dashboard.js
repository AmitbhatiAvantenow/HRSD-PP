import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, onWillDestroy, onWillStart, useState } from "@odoo/owl";

const STRIP_HTML = /<[^>]*>/g;
const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DONUT_COLORS = ["#6d5ef8", "#06b6d4", "#f97316", "#16a34a", "#ec4899", "#0891b2"];
const DONUT_RADIUS = 54;
const DONUT_CIRCUMFERENCE = 2 * Math.PI * DONUT_RADIUS;

function toDateStr(d) {
    return d.toISOString().slice(0, 10);
}

function formatHM(hours) {
    const total = Math.max(0, Math.round((hours || 0) * 60));
    const h = Math.floor(total / 60);
    const m = total % 60;
    return `${h}h ${String(m).padStart(2, "0")}m`;
}

export class HrTimesheetProDashboard extends Component {
    static template = "hr_timesheet_pro.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.formatHM = formatHM;

        this.state = useState({
            isHr: false,
            userName: user.name,
            kpis: {},
            kpiDisplay: {},
            weekDays: [],
            pendingApprovals: [],
            recentSheets: [],
            recentActivity: [],
            teamSnapshot: [],
            weekTarget: 40,
            monthTarget: 174,
            weekHours: 0,
            monthHours: 0,
            loading: true,
            chartsReady: false,
        });

        this._countUpRaf = null;
        onWillDestroy(() => {
            if (this._countUpRaf) cancelAnimationFrame(this._countUpRaf);
        });

        onWillStart(() => this.loadData());
    }

    get monday() {
        const today = new Date();
        const day = today.getDay();
        const diff = (day === 0 ? -6 : 1) - day;
        const monday = new Date(today);
        monday.setDate(today.getDate() + diff);
        monday.setHours(0, 0, 0, 0);
        return monday;
    }

    async loadData() {
        this.state.chartsReady = false;
        this.state.isHr = await user.hasGroup("hr_timesheet_pro.group_timesheet_pro_manager");
        const today = new Date();
        const todayStr = toDateStr(today);
        const monday = this.monday;
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        const monthStart = toDateStr(new Date(today.getFullYear(), today.getMonth(), 1));

        const ownDomain = [["employee_id.user_id", "=", user.userId]];
        const scopeDomain = this.state.isHr ? [] : ownDomain;

        const [company] = await this.orm.searchRead(
            "res.company", [], ["timesheet_pro_weekly_target_hours"], { limit: 1 }
        );
        const weeklyTarget = (company && company.timesheet_pro_weekly_target_hours) || 40;

        const sheets = await this.orm.searchRead(
            "hr.timesheet.sheet",
            scopeDomain,
            ["name", "employee_id", "date_start", "date_end", "week_number", "total_hours",
             "state", "submitted_date", "approved_date", "write_date"],
            { order: "date_start desc", limit: this.state.isHr ? 200 : 50 }
        );

        const lines = await this.orm.searchRead(
            "hr.timesheet.line",
            [...ownDomain, ["date", ">=", toDateStr(monday)], ["date", "<=", toDateStr(sunday)]],
            ["date", "hours"]
        );

        this.state.weekDays = Array.from({ length: 7 }, (_, i) => {
            const d = new Date(monday);
            d.setDate(monday.getDate() + i);
            const dStr = toDateStr(d);
            const hours = lines.filter((l) => l.date === dStr).reduce((s, l) => s + l.hours, 0);
            return { label: DAY_LABELS[i], date: dStr, hours, isToday: dStr === todayStr };
        });

        const monthDomain = this.state.isHr
            ? [["date", ">=", monthStart]]
            : [...ownDomain, ["date", ">=", monthStart]];
        const monthLines = await this.orm.searchRead("hr.timesheet.line", monthDomain, ["date", "hours"]);

        const weekTotal = this.state.isHr
            ? sheets.filter((s) => s.date_start === toDateStr(monday)).reduce((s, x) => s + x.total_hours, 0)
            : this.state.weekDays.reduce((s, d) => s + d.hours, 0);
        const todayTotal = this.state.weekDays.find((d) => d.isToday)?.hours || 0;
        const monthTotal = monthLines.reduce((s, l) => s + l.hours, 0);

        const pending = sheets.filter((s) => s.state === "submitted");
        const approved = sheets.filter((s) => s.state === "approved");
        const rejected = sheets.filter((s) => s.state === "rejected");

        let activeEmployeeCount = 1;
        if (this.state.isHr) {
            const employees = new Set(sheets.map((s) => s.employee_id && s.employee_id[0]));
            activeEmployeeCount = Math.max(1, employees.size);
            this.state.kpis = {
                teamHoursWeek: Math.round(weekTotal * 100) / 100,
                activeEmployees: employees.size,
                pendingApproval: pending.length,
                approvedMonth: approved.length,
                rejectedMonth: rejected.length,
                overtime: sheets.filter((s) => s.total_hours > weeklyTarget).length,
            };
            const byEmployee = {};
            for (const s of sheets) {
                if (!s.employee_id) continue;
                const key = s.employee_id[0];
                byEmployee[key] = byEmployee[key] || { name: s.employee_id[1], hours: 0 };
                byEmployee[key].hours += s.total_hours;
            }
            this.state.teamSnapshot = Object.values(byEmployee)
                .sort((a, b) => b.hours - a.hours)
                .slice(0, 6);
            this.state.pendingApprovals = pending.slice(0, 8);
        } else {
            this.state.kpis = {
                todayHours: Math.round(todayTotal * 100) / 100,
                weekHours: Math.round(weekTotal * 100) / 100,
                monthHours: Math.round(monthTotal * 100) / 100,
                pendingApproval: pending.length,
                approvedMonth: approved.length,
                rejectedMonth: rejected.length,
            };
        }
        this.state.recentSheets = sheets.slice(0, 8);

        this.state.weekTarget = Math.round(weeklyTarget * activeEmployeeCount * 100) / 100;
        this.state.monthTarget = Math.round(weeklyTarget * activeEmployeeCount * 4.345 * 100) / 100;
        this.state.weekHours = Math.round(weekTotal * 100) / 100;
        this.state.monthHours = Math.round(monthTotal * 100) / 100;

        const messages = await this.orm.searchRead(
            "mail.message",
            [["model", "=", "hr.timesheet.sheet"], ["res_id", "in", sheets.slice(0, 50).map((s) => s.id)]],
            ["res_id", "body", "date", "author_id"],
            { limit: 8, order: "id desc" }
        );
        const nameById = {};
        sheets.forEach((s) => { nameById[s.id] = s.name; });
        this.state.recentActivity = messages.map((m) => ({
            ...m,
            preview: (m.body || "").replace(STRIP_HTML, " ").trim().slice(0, 140),
            sheetName: nameById[m.res_id] || "",
        })).filter((m) => m.preview);

        this.state.loading = false;
        this._animateKpis();
        // Deferred so the DOM has the "before" state painted first, letting
        // the CSS transitions on the rings/donut actually animate in.
        setTimeout(() => { this.state.chartsReady = true; }, 60);
    }

    _animateKpis() {
        const cards = this.kpiCards;
        const from = { ...this.state.kpiDisplay };
        const to = {};
        cards.forEach((c) => { to[c.key] = c.value || 0; });
        const start = performance.now();
        const duration = 700;
        if (this._countUpRaf) cancelAnimationFrame(this._countUpRaf);
        const tick = (now) => {
            const t = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - t, 3);
            const next = {};
            cards.forEach((c) => {
                const f = from[c.key] || 0;
                next[c.key] = Math.round((f + (to[c.key] - f) * eased) * 10) / 10;
            });
            this.state.kpiDisplay = next;
            if (t < 1) {
                this._countUpRaf = requestAnimationFrame(tick);
            } else {
                this.state.kpiDisplay = to;
            }
        };
        this._countUpRaf = requestAnimationFrame(tick);
    }

    get kpiCards() {
        const k = this.state.kpis;
        if (this.state.isHr) {
            return [
                { key: "teamHoursWeek", label: "Team Hours (Week)", value: k.teamHoursWeek, icon: "fa-users", color: "indigo" },
                { key: "activeEmployees", label: "Active Employees", value: k.activeEmployees, icon: "fa-id-badge", color: "cyan" },
                { key: "pendingApproval", label: "Pending Approval", value: k.pendingApproval, icon: "fa-hourglass-half", color: "amber" },
                { key: "approvedMonth", label: "Approved (Month)", value: k.approvedMonth, icon: "fa-check-circle", color: "green" },
                { key: "rejectedMonth", label: "Rejected (Month)", value: k.rejectedMonth, icon: "fa-times-circle", color: "red" },
                { key: "overtime", label: "Overtime Sheets", value: k.overtime, icon: "fa-bolt", color: "amber" },
            ];
        }
        return [
            { key: "todayHours", label: "Today's Hours", value: k.todayHours, icon: "fa-clock-o", color: "indigo", suffix: "h" },
            { key: "weekHours", label: "This Week", value: k.weekHours, icon: "fa-calendar", color: "cyan", suffix: "h" },
            { key: "monthHours", label: "This Month", value: k.monthHours, icon: "fa-calendar-check-o", color: "green", suffix: "h" },
            { key: "pendingApproval", label: "Pending Approval", value: k.pendingApproval, icon: "fa-hourglass-half", color: "amber" },
            { key: "approvedMonth", label: "Approved (Month)", value: k.approvedMonth, icon: "fa-check-circle", color: "green" },
            { key: "rejectedMonth", label: "Rejected (Month)", value: k.rejectedMonth, icon: "fa-times-circle", color: "red" },
        ];
    }

    get kpiCardsDisplay() {
        return this.kpiCards.map((c) => ({
            ...c,
            displayValue: this.state.kpiDisplay[c.key] ?? 0,
        }));
    }

    get weekMaxHours() {
        return Math.max(8, ...this.state.weekDays.map((d) => d.hours));
    }

    get monthProgressPct() {
        return Math.min(100, Math.round((this.state.monthHours / (this.state.monthTarget || 1)) * 100));
    }

    get monthRingOffset() {
        const circumference = 2 * Math.PI * 40;
        const pct = this.state.chartsReady ? this.monthProgressPct : 0;
        return circumference - (pct / 100) * circumference;
    }

    get weekStatus() {
        const ratio = this.state.weekHours / (this.state.weekTarget || 1);
        if (ratio >= 1.05) return { key: "ahead", label: "Ahead", icon: "fa-arrow-up" };
        if (ratio >= 0.6) return { key: "on_track", label: "On Track", icon: "fa-check" };
        return { key: "behind", label: "Behind", icon: "fa-exclamation" };
    }

    get donutSegments() {
        const total = this.state.teamSnapshot.reduce((s, e) => s + e.hours, 0) || 1;
        let cumulativePct = 0;
        return this.state.teamSnapshot.map((e, i) => {
            const pct = (e.hours / total) * 100;
            const dashLength = this.state.chartsReady ? (pct / 100) * DONUT_CIRCUMFERENCE : 0;
            const seg = {
                name: e.name,
                hours: Math.round(e.hours * 100) / 100,
                pct: Math.round(pct),
                color: DONUT_COLORS[i % DONUT_COLORS.length],
                dasharray: `${dashLength} ${DONUT_CIRCUMFERENCE - dashLength}`,
                dashoffset: -((cumulativePct / 100) * DONUT_CIRCUMFERENCE),
            };
            cumulativePct += pct;
            return seg;
        });
    }

    get donutTotalHours() {
        return Math.round(this.state.teamSnapshot.reduce((s, e) => s + e.hours, 0) * 100) / 100;
    }

    stateBadgeClass(state) {
        return { draft: "muted", submitted: "warning", approved: "success", rejected: "danger", returned: "info" }[state] || "muted";
    }

    openLogTime() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "hr_timesheet_pro_log_time_wizard",
            name: "Log Time",
            target: "new",
        });
    }

    openWeekly() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "hr_timesheet_pro_fill_wizard",
            name: "Submit Weekly Timesheet",
            target: "new",
        });
    }

    openAction(xmlId) {
        this.action.doAction(xmlId);
    }

    openSheet(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.timesheet.sheet",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async quickApprove(id, ev) {
        ev.stopPropagation();
        await this.orm.call("hr.timesheet.sheet", "action_approve", [[id]]);
        this.notification.add("Timesheet approved.", { type: "success" });
        this.loadData();
    }

    async quickReject(id, ev) {
        ev.stopPropagation();
        await this.orm.call("hr.timesheet.sheet", "action_reject", [[id]]);
        this.notification.add("Timesheet rejected.", { type: "warning" });
        this.loadData();
    }

    deleteSheet(id, name, ev) {
        ev.stopPropagation();
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete Timesheet"),
            body: _t("Delete draft timesheet %s? This cannot be undone.", name),
            confirmLabel: _t("Delete"),
            confirmClass: "btn-danger",
            confirm: async () => {
                await this.orm.unlink("hr.timesheet.sheet", [id]);
                this.notification.add(_t("Timesheet deleted."), { type: "success" });
                this.loadData();
            },
            cancel: () => {},
        });
    }
}

registry.category("actions").add("hr_timesheet_pro_dashboard", HrTimesheetProDashboard);
