/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const STEPS = [
    { key: "employee", label: _t("Employee & Period"), icon: "fa-user" },
    { key: "worked", label: _t("Worked Days"), icon: "fa-clock-o" },
    { key: "earnings", label: _t("Earnings"), icon: "fa-arrow-up" },
    { key: "deductions", label: _t("Deductions"), icon: "fa-arrow-down" },
    { key: "review", label: _t("Review"), icon: "fa-check" },
];

const EARNING_CODES = ["BASIC", "HRACCA", "MEDICAL", "PROJALW"];
const DEDUCTION_CODES = ["EPF_EE", "LWF_EE"];

function toDateStr(d) {
    // Avoid toISOString() here: it converts to UTC first, which shifts
    // the date backward by a day for any timezone behind UTC (e.g. a
    // local-midnight "1st of the month" becomes "30th" in UTC).
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

export class HrPayslipCreateWizard extends Component {
    static template = "hr_payroll_community.PayslipCreateWizard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.steps = STEPS;

        const today = new Date();
        const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
        const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);

        this.state = useState({
            stepIndex: 0,
            employees: [],
            departments: [],
            employeeSearch: "",
            filterDeptId: false,
            filterStructure: "all", // all | set | unset
            selectedEmployeeIds: [],
            dateFrom: toDateStr(monthStart),
            dateTo: toDateStr(monthEnd),
            createdFor: null,
            duplicateInfo: null,
            duplicateConfirmedFor: null,
            checkingDuplicate: false,
            bulkDuplicateInfo: null, // [{employee_id, employee_name, slip_id, number, state}]
            bulkDuplicateConfirmedFor: null,
            bulkForceCreate: false,
            slipId: false,
            slipNumber: "",
            workedDays: [],
            inputs: [],
            lines: [],
            loadingStep: false,
            submitting: false,
            error: "",
            success: false,
            netPay: 0,
            // Bulk mode (2+ employees selected)
            bulkRunId: false,
            bulkResults: [],
            bulkValidating: false,
            bulkWorkedDays: [], // [{slip_id, employee_id, employee_name, lines: [...]}]
            bulkLines: [], // flat hr.payslip.line rows across all bulk slips
            bulkTableSearch: "",
            bulkEditSelectedIds: [], // slip_ids checked for the "Bulk Edit" action
            bulkEditField: "paid_days", // 'working_days' | 'paid_days'
            bulkEditValue: 0,
            showBulkEdit: false,
            bulkRowBusy: {}, // slip_id -> bool, per-row spinner
            // Pay (after validation)
            paymentMode: "advice", // advice | neft | cheque
            paymentDate: toDateStr(today),
            markingPaid: false,
            paidDone: false,
        });

        onWillStart(async () => {
            [this.state.employees, this.state.departments] = await Promise.all([
                this.orm.searchRead(
                    "hr.employee",
                    [["active", "=", true]],
                    ["id", "name", "job_title", "struct_id", "wage", "department_id"],
                    { order: "name" }
                ),
                this.orm.searchRead(
                    "hr.department", [], ["id", "name"], { order: "name" }
                ),
            ]);
        });
    }

    get currentStep() {
        return this.state.success ? "success" : this.steps[this.state.stepIndex].key;
    }
    get isFirstStep() { return this.state.stepIndex === 0; }
    get isLastStep() { return this.state.stepIndex === this.steps.length - 1; }
    get isBulk() { return this.state.selectedEmployeeIds.length > 1; }
    get progressPct() {
        if (this.state.success) return 100;
        return Math.round(((this.state.stepIndex + 1) / this.steps.length) * 100);
    }

    get employeeId() { return this.state.selectedEmployeeIds[0] || false; }
    get selectedEmployees() {
        const ids = new Set(this.state.selectedEmployeeIds);
        return this.state.employees.filter((e) => ids.has(e.id));
    }
    get employeeName() {
        const e = this.selectedEmployees[0];
        return e ? e.name : "";
    }

    get filteredEmployees() {
        const q = (this.state.employeeSearch || "").toLowerCase().trim();
        return this.state.employees.filter((emp) => {
            if (q && !(
                (emp.name || "").toLowerCase().includes(q) ||
                (emp.job_title || "").toLowerCase().includes(q)
            )) return false;
            if (this.state.filterDeptId
                && (!emp.department_id || emp.department_id[0] !== this.state.filterDeptId)) {
                return false;
            }
            if (this.state.filterStructure === "set" && !emp.struct_id) return false;
            if (this.state.filterStructure === "unset" && emp.struct_id) return false;
            return true;
        });
    }
    get allFilteredSelected() {
        const visible = this.filteredEmployees;
        return visible.length > 0 && visible.every(
            (e) => this.state.selectedEmployeeIds.includes(e.id));
    }

    toggleEmployee(emp) {
        const ids = this.state.selectedEmployeeIds;
        const idx = ids.indexOf(emp.id);
        if (idx === -1) ids.push(emp.id);
        else ids.splice(idx, 1);
        this.state.error = "";
        this.state.duplicateInfo = null;
        this.state.bulkDuplicateInfo = null;
    }

    selectAllFiltered() {
        const ids = new Set(this.state.selectedEmployeeIds);
        for (const emp of this.filteredEmployees) ids.add(emp.id);
        this.state.selectedEmployeeIds = [...ids];
        this.state.duplicateInfo = null;
        this.state.bulkDuplicateInfo = null;
    }

    clearSelection() {
        this.state.selectedEmployeeIds = [];
        this.state.duplicateInfo = null;
        this.state.bulkDuplicateInfo = null;
    }

    onSearchInput(ev) { this.state.employeeSearch = ev.target.value; }
    onBulkTableSearchInput(ev) { this.state.bulkTableSearch = ev.target.value; }
    onFilterDeptChange(ev) {
        this.state.filterDeptId = ev.target.value ? parseInt(ev.target.value, 10) : false;
    }
    setFilterStructure(value) { this.state.filterStructure = value; }

    _periodSignature() {
        return `${this.employeeId}|${this.state.dateFrom}|${this.state.dateTo}`;
    }

    _bulkPeriodSignature() {
        const ids = [...this.state.selectedEmployeeIds].sort((a, b) => a - b).join(",");
        return `${ids}|${this.state.dateFrom}|${this.state.dateTo}`;
    }

    avatarColor(id) {
        const colors = ["indigo", "rose", "sky", "mint", "amber"];
        return colors[Math.abs(id || 0) % colors.length];
    }

    linesByCodes(codes) {
        return this.state.lines.filter((l) => codes.includes(l.code));
    }

    get earningLines() { return this.linesByCodes(EARNING_CODES); }
    get deductionLines() { return this.linesByCodes(DEDUCTION_CODES); }
    get grossTotal() { return this.lineTotal("GROSS"); }
    get netTotal() { return this.lineTotal("NET"); }
    get ctcTotal() { return this.lineTotal("CTC"); }

    lineTotal(code) {
        const line = this.state.lines.find((l) => l.code === code);
        return line ? line.total : 0;
    }

    get bulkCreatedResults() { return this.state.bulkResults.filter((r) => r.status === "created"); }
    get bulkValidatedResults() { return this.state.bulkResults.filter((r) => r.status === "validated"); }
    get bulkSkippedResults() { return this.state.bulkResults.filter((r) => r.status === "skipped"); }
    get bulkErrorResults() { return this.state.bulkResults.filter((r) => r.status === "error"); }
    get bulkNetTotal() {
        const source = this.bulkValidatedResults.length ? this.bulkValidatedResults : this.bulkCreatedResults;
        return source.reduce((sum, r) => sum + (r.net_total || 0), 0);
    }

    inputByCode(code) {
        return this.state.inputs.find((i) => i.code === code);
    }

    // Ad-hoc earning/deduction lines added via "+ Add Earning"/"+ Add
    // Deduction" - each is its own hr.payslip.input (unique EXTRAEARN_*/
    // EXTRADED_* code) so it can be individually named/edited/removed;
    // a single "Other Earnings"/"Other Deductions" salary rule sums
    // them into the payslip total (see hr_payroll_structure_india_regular.xml).
    get extraEarnings() {
        return this.state.inputs.filter((i) => i.code && i.code.startsWith("EXTRAEARN"));
    }
    get extraDeductions() {
        return this.state.inputs.filter((i) => i.code && i.code.startsWith("EXTRADED"));
    }

    formatMoney(amount) {
        return "Rs. " + (amount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    canProceed() {
        if (this.currentStep === "employee") {
            return this.state.selectedEmployeeIds.length > 0 && !!this.state.dateFrom && !!this.state.dateTo;
        }
        return true;
    }

    async goNext() {
        if (!this.canProceed()) {
            this.state.error = _t("Please pick at least one employee and a period first.");
            return;
        }
        this.state.error = "";
        if (this.currentStep === "employee") {
            if (this.isBulk) {
                const bulkSig = this._bulkPeriodSignature();
                if (this.state.bulkDuplicateConfirmedFor !== bulkSig) {
                    this.state.checkingDuplicate = true;
                    let conflicts;
                    try {
                        conflicts = await this.orm.call(
                            "hr.payslip", "check_bulk_duplicates",
                            [this.state.selectedEmployeeIds, this.state.dateFrom, this.state.dateTo]
                        );
                    } catch (e) {
                        this.state.checkingDuplicate = false;
                        this.state.error = this._errorMessage(e);
                        return;
                    }
                    this.state.checkingDuplicate = false;
                    if (conflicts.length) {
                        this.state.bulkDuplicateInfo = conflicts;
                        return;
                    }
                }
                this.state.bulkDuplicateInfo = null;
                await this._runBulkGenerate();
                if (this.state.error) return;
                await Promise.all([this._loadBulkWorkedDays(), this._loadBulkLines()]);
                if (!this.isLastStep) this.state.stepIndex++;
                return;
            }
            const stale = !this.state.slipId || !this.state.createdFor
                || this.state.createdFor.employeeId !== this.employeeId
                || this.state.createdFor.dateFrom !== this.state.dateFrom
                || this.state.createdFor.dateTo !== this.state.dateTo;
            if (stale) {
                const sig = this._periodSignature();
                if (this.state.duplicateConfirmedFor !== sig) {
                    this.state.checkingDuplicate = true;
                    let duplicate;
                    try {
                        duplicate = await this.orm.call(
                            "hr.payslip", "find_duplicate_payslip",
                            [this.employeeId, this.state.dateFrom, this.state.dateTo]
                        );
                    } catch (e) {
                        this.state.checkingDuplicate = false;
                        this.state.error = this._errorMessage(e);
                        return;
                    }
                    this.state.checkingDuplicate = false;
                    if (duplicate) {
                        this.state.duplicateInfo = duplicate;
                        return;
                    }
                }
                this.state.duplicateInfo = null;
                if (this.state.slipId) {
                    try { await this.orm.unlink("hr.payslip", [this.state.slipId]); } catch { /* best effort */ }
                    this.state.slipId = false;
                }
                await this._createAndCompute();
                if (this.state.error) return;
            }
        }
        if (this.isBulk && this.currentStep === "deductions") {
            this._refreshBulkNetTotals();
        }
        if (!this.isLastStep) this.state.stepIndex++;
    }

    openExistingPayslip() {
        const id = this.state.duplicateInfo && this.state.duplicateInfo.id;
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.payslip",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    confirmCreateDuplicate() {
        this.state.duplicateConfirmedFor = this._periodSignature();
        this.state.duplicateInfo = null;
        this.goNext();
    }

    openBulkDuplicate(conflict) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.payslip",
            res_id: conflict.slip_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    confirmBulkSkipDuplicates() {
        this.state.bulkDuplicateConfirmedFor = this._bulkPeriodSignature();
        this.state.bulkForceCreate = false;
        this.state.bulkDuplicateInfo = null;
        this.goNext();
    }

    confirmBulkCreateDuplicates() {
        this.state.bulkDuplicateConfirmedFor = this._bulkPeriodSignature();
        this.state.bulkForceCreate = true;
        this.state.bulkDuplicateInfo = null;
        this.goNext();
    }

    goBack() {
        this.state.error = "";
        if (!this.isFirstStep) this.state.stepIndex--;
    }

    goToStep(index) {
        if (this.state.success || index > this.state.stepIndex) return;
        this.state.stepIndex = index;
    }

    async _runBulkGenerate() {
        this.state.loadingStep = true;
        this.state.bulkResults = [];
        this.state.bulkRunId = false;
        try {
            const res = await this.orm.call(
                "hr.payslip", "bulk_generate",
                [this.state.selectedEmployeeIds, this.state.dateFrom, this.state.dateTo],
                { force: this.state.bulkForceCreate }
            );
            this.state.bulkRunId = res.run_id;
            this.state.bulkResults = res.results;
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    async _loadBulkWorkedDays() {
        const slipIds = this.bulkCreatedResults.map((r) => r.slip_id);
        if (!slipIds.length) { this.state.bulkWorkedDays = []; return; }
        const wdRecords = await this.orm.searchRead(
            "hr.payslip.worked.days",
            [["payslip_id", "in", slipIds]],
            ["name", "code", "number_of_days", "number_of_hours", "payslip_id"],
            { order: "payslip_id, sequence" }
        );
        const byId = {};
        for (const r of this.bulkCreatedResults) {
            byId[r.slip_id] = {
                slip_id: r.slip_id, employee_id: r.employee_id,
                employee_name: r.employee_name, lines: [],
            };
        }
        for (const wd of wdRecords) {
            const key = wd.payslip_id[0];
            if (byId[key]) byId[key].lines.push(wd);
        }
        this.state.bulkWorkedDays = Object.values(byId);
    }

    async _loadBulkLines() {
        const slipIds = this.bulkCreatedResults.map((r) => r.slip_id);
        if (!slipIds.length) { this.state.bulkLines = []; return; }
        this.state.bulkLines = await this.orm.searchRead(
            "hr.payslip.line",
            [["slip_id", "in", slipIds]],
            ["code", "name", "total", "slip_id"]
        );
    }

    _refreshBulkNetTotals() {
        for (const r of this.state.bulkResults) {
            if (r.status !== "created") continue;
            const netLine = this.state.bulkLines.find(
                (l) => l.slip_id[0] === r.slip_id && l.code === "NET");
            r.net_total = netLine ? netLine.total : 0;
        }
    }

    get bulkWorkedDaysFiltered() {
        const q = (this.state.bulkTableSearch || "").toLowerCase().trim();
        if (!q) return this.state.bulkWorkedDays;
        return this.state.bulkWorkedDays.filter(
            (row) => row.employee_name.toLowerCase().includes(q));
    }

    _wdLine(row, code) {
        return row.lines.find((l) => l.code === code);
    }
    wdValue(row, code, field) {
        const line = this._wdLine(row, code);
        return line ? line[field] : 0;
    }

    async onBulkWdFieldChange(row, code, field, ev) {
        const value = parseFloat(ev.target.value) || 0;
        const line = this._wdLine(row, code);
        if (!line) return;
        line[field] = value;
        this.state.bulkRowBusy = { ...this.state.bulkRowBusy, [row.slip_id]: true };
        try {
            await this.orm.write("hr.payslip.worked.days", [line.id], { [field]: value });
            await this.orm.call("hr.payslip", "action_compute_sheet", [[row.slip_id]]);
            const newLines = await this.orm.searchRead(
                "hr.payslip.line", [["slip_id", "=", row.slip_id]],
                ["code", "name", "total", "slip_id"]
            );
            this.state.bulkLines = this.state.bulkLines
                .filter((l) => l.slip_id[0] !== row.slip_id)
                .concat(newLines);
            this._refreshBulkNetTotals();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            const busy = { ...this.state.bulkRowBusy };
            delete busy[row.slip_id];
            this.state.bulkRowBusy = busy;
        }
    }

    async removeBulkEmployee(row) {
        this.state.loadingStep = true;
        try {
            await this.orm.unlink("hr.payslip", [row.slip_id]);
            this.state.bulkResults = this.state.bulkResults.filter((r) => r.slip_id !== row.slip_id);
            this.state.bulkWorkedDays = this.state.bulkWorkedDays.filter((r) => r.slip_id !== row.slip_id);
            this.state.bulkLines = this.state.bulkLines.filter((l) => l.slip_id[0] !== row.slip_id);
            this.state.bulkEditSelectedIds = this.state.bulkEditSelectedIds.filter((id) => id !== row.slip_id);
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    toggleBulkEditRow(row) {
        const ids = this.state.bulkEditSelectedIds;
        const idx = ids.indexOf(row.slip_id);
        if (idx === -1) ids.push(row.slip_id);
        else ids.splice(idx, 1);
    }
    get allBulkEditSelected() {
        const visible = this.bulkWorkedDaysFiltered;
        return visible.length > 0 && visible.every(
            (r) => this.state.bulkEditSelectedIds.includes(r.slip_id));
    }
    toggleBulkEditAll() {
        if (this.allBulkEditSelected) {
            this.state.bulkEditSelectedIds = [];
        } else {
            this.state.bulkEditSelectedIds = this.bulkWorkedDaysFiltered.map((r) => r.slip_id);
        }
    }
    toggleShowBulkEdit() { this.state.showBulkEdit = !this.state.showBulkEdit; }
    onBulkEditFieldChange(ev) { this.state.bulkEditField = ev.target.value; }
    onBulkEditValueChange(ev) { this.state.bulkEditValue = parseFloat(ev.target.value) || 0; }

    async applyBulkEdit() {
        const slipIds = this.state.bulkEditSelectedIds;
        if (!slipIds.length) {
            this.state.error = _t("Select at least one row to bulk-edit.");
            return;
        }
        const code = this.state.bulkEditField === "working_days" ? "WORKING_DAYS" : "PAID_DAYS";
        this.state.loadingStep = true;
        try {
            await this.orm.call("hr.payslip", "bulk_set_worked_days", [
                slipIds, code, "number_of_days", this.state.bulkEditValue,
            ]);
            await Promise.all([this._loadBulkWorkedDays(), this._loadBulkLines()]);
            this._refreshBulkNetTotals();
            this.state.showBulkEdit = false;
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    linesByCodesFor(slipId, codes) {
        return this.state.bulkLines.filter(
            (l) => l.slip_id[0] === slipId && codes.includes(l.code));
    }

    get bulkEarningComponents() { return this._bulkComponents(EARNING_CODES); }
    get bulkDeductionComponents() { return this._bulkComponents(DEDUCTION_CODES); }

    _bulkComponents(codes) {
        const total = this.bulkCreatedResults.length;
        return codes.map((code) => {
            const rows = this.state.bulkLines.filter((l) => l.code === code);
            const impacted = rows.filter((l) => l.total).length;
            return {
                code,
                name: rows.length ? rows[0].name : code,
                total: rows.reduce((sum, l) => sum + l.total, 0),
                impacted,
                total_employees: total,
            };
        });
    }
    get bulkEarningsTotal() {
        return this.bulkEarningComponents.reduce((s, c) => s + c.total, 0);
    }
    get bulkDeductionsTotal() {
        return this.bulkDeductionComponents.reduce((s, c) => s + c.total, 0);
    }

    _lineTotalFor(slipId, code) {
        const line = this.state.bulkLines.find(
            (l) => l.slip_id[0] === slipId && l.code === code);
        return line ? line.total : 0;
    }

    // Per-employee rows, shown under the combined component table so you
    // can see (and sanity-check) each individual employee's breakdown,
    // not just the summed-up totals.
    get bulkEarningsPerEmployee() {
        return this.bulkCreatedResults.map((r) => ({
            slip_id: r.slip_id,
            employee_name: r.employee_name,
            basic: this._lineTotalFor(r.slip_id, "BASIC"),
            hraCca: this._lineTotalFor(r.slip_id, "HRACCA"),
            medical: this._lineTotalFor(r.slip_id, "MEDICAL"),
            projalw: this._lineTotalFor(r.slip_id, "PROJALW"),
            bonus: this._lineTotalFor(r.slip_id, "BONUSAMT"),
            gross: this._lineTotalFor(r.slip_id, "GROSS"),
        }));
    }
    get bulkDeductionsPerEmployee() {
        return this.bulkCreatedResults.map((r) => {
            const epf = this._lineTotalFor(r.slip_id, "EPF_EE");
            const lwf = this._lineTotalFor(r.slip_id, "LWF_EE");
            const tds = this._lineTotalFor(r.slip_id, "TDSAMT");
            const addl = this._lineTotalFor(r.slip_id, "ADDLDEDAMT");
            return {
                slip_id: r.slip_id,
                employee_name: r.employee_name,
                epf, lwf, tds, addl,
                total: epf + lwf + tds + addl,
            };
        });
    }

    async _bulkApplyInput(code, amount) {
        const slipIds = this.bulkCreatedResults.map((r) => r.slip_id);
        if (!slipIds.length) return;
        this.state.loadingStep = true;
        try {
            await this.orm.call("hr.payslip", "bulk_set_input", [slipIds, code, amount]);
            await this._loadBulkLines();
            this._refreshBulkNetTotals();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }
    onBulkBonusChange(ev) { this._bulkApplyInput("BONUS", parseFloat(ev.target.value) || 0); }
    onBulkTdsChange(ev) { this._bulkApplyInput("TDS", parseFloat(ev.target.value) || 0); }

    // Same idea as _bulkApplyInput but scoped to one employee's payslip,
    // for editing a single cell in the per-employee breakdown table
    // instead of the same amount for everyone in the batch.
    async onBulkPerEmployeeInputChange(slipId, code, ev) {
        const amount = parseFloat(ev.target.value) || 0;
        this.state.bulkRowBusy = { ...this.state.bulkRowBusy, [slipId]: true };
        try {
            await this.orm.call("hr.payslip", "bulk_set_input", [[slipId], code, amount]);
            const newLines = await this.orm.searchRead(
                "hr.payslip.line", [["slip_id", "=", slipId]],
                ["code", "name", "total", "slip_id"]
            );
            this.state.bulkLines = this.state.bulkLines
                .filter((l) => l.slip_id[0] !== slipId)
                .concat(newLines);
            this._refreshBulkNetTotals();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            const busy = { ...this.state.bulkRowBusy };
            delete busy[slipId];
            this.state.bulkRowBusy = busy;
        }
    }
    onBulkAddlDedChange(ev) { this._bulkApplyInput("ADDLDED", parseFloat(ev.target.value) || 0); }

    async onValidateBulk() {
        const ids = this.bulkCreatedResults.map((r) => r.slip_id);
        if (!ids.length) {
            this.state.error = _t("Nothing to validate - no payslips were created.");
            return;
        }
        this.state.bulkValidating = true;
        this.state.error = "";
        try {
            // Isolated per-payslip on the server: one employee with no
            // computed lines (no Salary Structure) must not block the
            // rest of the batch from validating.
            const results = await this.orm.call("hr.payslip", "bulk_validate", [ids]);
            const byId = {};
            for (const r of results) byId[r.slip_id] = r;
            for (const r of this.state.bulkResults) {
                const outcome = byId[r.slip_id];
                if (!outcome) continue;
                if (outcome.status === "validated") {
                    r.status = "validated";
                    r.net_total = outcome.net_total;
                } else {
                    r.status = "error";
                    r.reason = outcome.reason;
                }
            }
            this.state.netPay = this.bulkNetTotal;
            this.state.success = true;
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.bulkValidating = false;
        }
    }

    viewBulkRun() {
        if (!this.state.bulkRunId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.payslip.run",
            res_id: this.state.bulkRunId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async _createAndCompute() {
        this.state.loadingStep = true;
        try {
            const ids = await this.orm.create("hr.payslip", [{
                employee_id: this.employeeId,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
            }]);
            this.state.slipId = ids[0];
            this.state.createdFor = {
                employeeId: this.employeeId,
                dateFrom: this.state.dateFrom,
                dateTo: this.state.dateTo,
            };
            await this.orm.call("hr.payslip", "action_recompute_worked_days", [[this.state.slipId]]);
            await this._refreshAll();
        } catch (e) {
            this.state.error = this._errorMessage(e);
            if (this.state.slipId) {
                try { await this.orm.unlink("hr.payslip", [this.state.slipId]); } catch { /* best effort */ }
                this.state.slipId = false;
                this.state.createdFor = null;
            }
        } finally {
            this.state.loadingStep = false;
        }
    }

    async _refreshAll() {
        const [slip] = await this.orm.read(
            "hr.payslip", [this.state.slipId],
            ["number", "worked_days_line_ids", "input_line_ids", "line_ids"]
        );
        this.state.slipNumber = slip.number;
        this.state.workedDays = await this.orm.read(
            "hr.payslip.worked.days", slip.worked_days_line_ids,
            ["name", "code", "number_of_days", "number_of_hours"]
        );
        this.state.inputs = await this.orm.read(
            "hr.payslip.input", slip.input_line_ids, ["name", "code", "amount"]
        );
        this.state.lines = await this.orm.read(
            "hr.payslip.line", slip.line_ids, ["name", "code", "total", "category_id"]
        );
    }

    async refreshWorkedDays() {
        this.state.loadingStep = true;
        try {
            await this.orm.call("hr.payslip", "action_recompute_worked_days", [[this.state.slipId]]);
            await this._refreshAll();
            this.notification.add(_t("Refreshed from Timesheets & Time Off."), { type: "success" });
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    async _recomputeAndRefreshLines() {
        await this.orm.call("hr.payslip", "action_compute_sheet", [[this.state.slipId]]);
        const [slip] = await this.orm.read("hr.payslip", [this.state.slipId], ["line_ids"]);
        this.state.lines = await this.orm.read(
            "hr.payslip.line", slip.line_ids, ["name", "code", "total", "category_id"]
        );
    }

    async onWorkedDayFieldChange(line, fieldName, ev) {
        const isNumeric = fieldName === "number_of_days" || fieldName === "number_of_hours";
        const value = isNumeric ? (parseFloat(ev.target.value) || 0) : ev.target.value;
        line[fieldName] = value;
        this.state.loadingStep = true;
        try {
            await this.orm.write("hr.payslip.worked.days", [line.id], { [fieldName]: value });
            await this._recomputeAndRefreshLines();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    async addWorkedDayLine() {
        this.state.loadingStep = true;
        try {
            const [slip] = await this.orm.read("hr.payslip", [this.state.slipId], ["contract_id"]);
            if (!slip.contract_id) {
                this.state.error = _t("No contract found for this employee/period - cannot add a line.");
                return;
            }
            const [id] = await this.orm.create("hr.payslip.worked.days", [{
                payslip_id: this.state.slipId,
                contract_id: slip.contract_id[0],
                name: _t("New Entry"),
                code: "",
                number_of_days: 0,
                number_of_hours: 0,
            }]);
            const [line] = await this.orm.read(
                "hr.payslip.worked.days", [id],
                ["name", "code", "number_of_days", "number_of_hours"]
            );
            this.state.workedDays.push(line);
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    async removeWorkedDayLine(line) {
        this.state.loadingStep = true;
        try {
            await this.orm.unlink("hr.payslip.worked.days", [line.id]);
            this.state.workedDays = this.state.workedDays.filter((l) => l.id !== line.id);
            await this._recomputeAndRefreshLines();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    async onInputChange(code, ev) {
        const input = this.inputByCode(code);
        if (!input) return;
        const amount = parseFloat(ev.target.value) || 0;
        input.amount = amount;
        await this.orm.write("hr.payslip.input", [input.id], { amount });
        await this.orm.call("hr.payslip", "action_compute_sheet", [[this.state.slipId]]);
        const [slip] = await this.orm.read("hr.payslip", [this.state.slipId], ["line_ids"]);
        this.state.lines = await this.orm.read(
            "hr.payslip.line", slip.line_ids, ["name", "code", "total", "category_id"]
        );
    }

    // Editing an auto-computed Earnings/Deductions row (Basic, CCA+HRA,
    // Medical, Project Allowance, EPF, LWF): stored as a "<CODE>_ADJ"
    // hr.payslip.input. The salary rule for that code uses the override
    // amount instead of its formula whenever that input is present (see
    // hr_payroll_structure_india_regular.xml), so this never touches the
    // rule/formula itself - it's a per-payslip override only.
    async onAutoLineChange(line, ev) {
        const adjCode = `${line.code}_ADJ`;
        const raw = parseFloat(ev.target.value) || 0;
        this.state.loadingStep = true;
        try {
            const existing = this.state.inputs.find((i) => i.code === adjCode);
            if (existing) {
                existing.amount = raw;
                await this.orm.write("hr.payslip.input", [existing.id], { amount: raw });
            } else {
                const [slip] = await this.orm.read("hr.payslip", [this.state.slipId], ["contract_id"]);
                if (!slip.contract_id) {
                    this.state.error = _t("No contract found for this employee/period - cannot override this line.");
                    return;
                }
                const [id] = await this.orm.create("hr.payslip.input", [{
                    payslip_id: this.state.slipId,
                    contract_id: slip.contract_id[0],
                    name: `${line.name} (${_t("Manual Override")})`,
                    code: adjCode,
                    amount: raw,
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo,
                }]);
                this.state.inputs.push({
                    id, code: adjCode, amount: raw,
                    name: `${line.name} (${_t("Manual Override")})`,
                });
            }
            await this._recomputeAndRefreshLines();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    // "+ Add Earning" / "+ Add Deduction": create a new named, freely
    // editable extra line (see extraEarnings/extraDeductions above).
    async addExtraLine(kind) {
        const prefix = kind === "earning" ? "EXTRAEARN" : "EXTRADED";
        const label = kind === "earning" ? _t("New Earning") : _t("New Deduction");
        this.state.loadingStep = true;
        try {
            const [slip] = await this.orm.read("hr.payslip", [this.state.slipId], ["contract_id"]);
            if (!slip.contract_id) {
                this.state.error = _t("No contract found for this employee/period - cannot add a line.");
                return;
            }
            const code = `${prefix}_${Date.now()}`;
            const [id] = await this.orm.create("hr.payslip.input", [{
                payslip_id: this.state.slipId,
                contract_id: slip.contract_id[0],
                name: label,
                code,
                amount: 0,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
            }]);
            this.state.inputs.push({ id, name: label, code, amount: 0 });
            await this._recomputeAndRefreshLines();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    async removeExtraLine(input) {
        this.state.loadingStep = true;
        try {
            await this.orm.unlink("hr.payslip.input", [input.id]);
            this.state.inputs = this.state.inputs.filter((i) => i.id !== input.id);
            await this._recomputeAndRefreshLines();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    async onExtraLineNameChange(input, ev) {
        const name = ev.target.value;
        input.name = name;
        try {
            await this.orm.write("hr.payslip.input", [input.id], { name });
        } catch (e) {
            this.state.error = this._errorMessage(e);
        }
    }

    async onExtraLineAmountChange(input, ev) {
        const amount = parseFloat(ev.target.value) || 0;
        input.amount = amount;
        this.state.loadingStep = true;
        try {
            await this.orm.write("hr.payslip.input", [input.id], { amount });
            await this._recomputeAndRefreshLines();
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.loadingStep = false;
        }
    }

    _errorMessage(e) {
        return (e && e.data && e.data.message) || (e && e.message) || _t("Something went wrong.");
    }

    async onValidate() {
        this.state.submitting = true;
        this.state.error = "";
        try {
            await this.orm.call("hr.payslip", "action_payslip_done", [[this.state.slipId]]);
            await this._refreshAll();
            this.state.netPay = this.netTotal;
            this.state.success = true;
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.submitting = false;
        }
    }

    onPaymentModeChange(ev) { this.state.paymentMode = ev.target.value; }
    onPaymentDateChange(ev) { this.state.paymentDate = ev.target.value; }

    async onMarkPaid() {
        const ids = this.isBulk
            ? this.bulkValidatedResults.map((r) => r.slip_id)
            : (this.state.slipId ? [this.state.slipId] : []);
        if (!ids.length) return;
        this.state.markingPaid = true;
        this.state.error = "";
        try {
            await this.orm.call("hr.payslip", "action_payslip_pay", [ids], {
                payment_mode: this.state.paymentMode,
                payment_date: this.state.paymentDate,
            });
            this.state.paidDone = true;
        } catch (e) {
            this.state.error = this._errorMessage(e);
        } finally {
            this.state.markingPaid = false;
        }
    }

    get previewUrl() {
        return this.state.slipId
            ? `/report/pdf/hr_payroll_community.report_payslip/${this.state.slipId}`
            : "";
    }

    viewPayslip() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.payslip",
            res_id: this.state.slipId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    printPayslip() {
        window.open(this.previewUrl, "_blank");
    }

    // The payslip report template loops over `docs`, so a comma-joined
    // id list in the URL renders every payslip into one combined PDF -
    // same mechanism as selecting multiple records and hitting Print
    // from the payslip list view.
    get bulkPreviewUrl() {
        const ids = this.bulkValidatedResults.map((r) => r.slip_id);
        return ids.length
            ? `/report/pdf/hr_payroll_community.report_payslip/${ids.join(",")}`
            : "";
    }

    printBulkPayslips() {
        if (this.bulkPreviewUrl) window.open(this.bulkPreviewUrl, "_blank");
    }

    createAnother() {
        this.state.stepIndex = 0;
        this.state.selectedEmployeeIds = [];
        this.state.slipId = false;
        this.state.createdFor = null;
        this.state.duplicateInfo = null;
        this.state.duplicateConfirmedFor = null;
        this.state.bulkDuplicateInfo = null;
        this.state.bulkDuplicateConfirmedFor = null;
        this.state.bulkForceCreate = false;
        this.state.slipNumber = "";
        this.state.workedDays = [];
        this.state.inputs = [];
        this.state.lines = [];
        this.state.bulkRunId = false;
        this.state.bulkResults = [];
        this.state.bulkWorkedDays = [];
        this.state.bulkLines = [];
        this.state.bulkTableSearch = "";
        this.state.bulkEditSelectedIds = [];
        this.state.showBulkEdit = false;
        this.state.paymentMode = "advice";
        this.state.markingPaid = false;
        this.state.paidDone = false;
        this.state.success = false;
        this.state.netPay = 0;
        this.state.error = "";
    }

    async onCancel() {
        if (this.state.slipId && !this.state.success) {
            try { await this.orm.unlink("hr.payslip", [this.state.slipId]); } catch { /* best effort */ }
        }
        if (this.isBulk && !this.state.success && this.bulkCreatedResults.length) {
            try {
                await this.orm.unlink("hr.payslip", this.bulkCreatedResults.map((r) => r.slip_id));
                if (this.state.bulkRunId) await this.orm.unlink("hr.payslip.run", [this.state.bulkRunId]);
            } catch { /* best effort */ }
        }
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }

    onClose() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("hr_payroll_community_payslip_wizard", HrPayslipCreateWizard);
