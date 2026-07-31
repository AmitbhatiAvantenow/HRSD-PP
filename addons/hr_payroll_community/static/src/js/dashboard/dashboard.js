/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";

function toDateStr(d) {
    // Avoid toISOString() here: it converts to UTC first, which shifts
    // the date backward by a day for any timezone behind UTC.
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

export class HrPayrollDashboard extends Component {
    static template = "hr_payroll_community.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            userName: user.name,
            period: "",
            kpis: {},
            needsAttention: [],
            recentPayslips: [],
            loading: true,
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        const today = new Date();
        const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
        const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        this.state.period = today.toLocaleString("default", { month: "long", year: "numeric" });

        const employees = await this.orm.searchRead(
            "hr.employee", [["active", "=", true]],
            ["name", "pan_number", "uan_number", "primary_bank_account_id"]
        );

        const payslips = await this.orm.searchRead(
            "hr.payslip",
            [["date_from", "<=", toDateStr(monthEnd)], ["date_to", ">=", toDateStr(monthStart)]],
            ["employee_id", "display_state", "contract_id", "date_to"],
            { order: "date_to desc" }
        );

        let netTotal = 0;
        if (payslips.length) {
            const netLines = await this.orm.searchRead(
                "hr.payslip.line",
                [["slip_id", "in", payslips.map((p) => p.id)], ["code", "=", "NET"]],
                ["total"]
            );
            netTotal = netLines.reduce((s, l) => s + l.total, 0);
        }

        const missingPan = employees.filter((e) => !e.pan_number);
        const missingUan = employees.filter((e) => !e.uan_number);
        const missingBank = employees.filter((e) => !e.primary_bank_account_id);
        const noContract = payslips.filter((p) => !p.contract_id);
        const draftCount = payslips.filter((p) => p.display_state === "draft").length;
        const validatedCount = payslips.filter((p) => p.display_state === "validated").length;
        const paidCount = payslips.filter((p) => p.display_state === "paid").length;

        this.state.kpis = {
            employees: employees.length,
            netPayroll: Math.round(netTotal).toLocaleString("en-IN"),
            pendingActions: missingPan.length + missingUan.length + missingBank.length + noContract.length,
            nextPayDate: monthEnd.toLocaleDateString("default", { day: "numeric", month: "short" }),
            draftCount,
            validatedCount,
            paidCount,
        };

        this.state.needsAttention = [
            missingBank.length && {
                label: `${missingBank.length} employee(s) missing bank account`,
                hint: "Required for direct salary disbursement.",
                severity: "danger",
                icon: "fa-university",
            },
            noContract.length && {
                label: `${noContract.length} payslip(s) without a running contract`,
                hint: "Payslips can't be validated correctly until one is configured.",
                severity: "danger",
                icon: "fa-exclamation-triangle",
            },
            missingPan.length && {
                label: `${missingPan.length} employee(s) without PAN number`,
                hint: "Required for TDS deduction and Form 16 filing.",
                severity: "info",
                icon: "fa-address-card-o",
            },
            missingUan.length && {
                label: `${missingUan.length} employee(s) without UAN number`,
                hint: "Needed to track Provident Fund contributions.",
                severity: "info",
                icon: "fa-shield",
            },
        ].filter(Boolean);

        this.state.recentPayslips = payslips.slice(0, 8);
        this.state.loading = false;
    }

    stateBadgeClass(state) {
        return { draft: "muted", validated: "info", paid: "success", cancel: "muted" }[state] || "muted";
    }

    openEmployees() {
        this.action.doAction("hr.open_view_employee_list");
    }

    openPayslips() {
        this.action.doAction("hr_payroll_community.hr_payslip_action");
    }

    openNewPayslip() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "hr_payroll_community_payslip_wizard",
            name: _t("New Payslip"),
            target: "new",
        });
    }

    openTimeOff() {
        this.action.doAction("hr_holidays.hr_leave_action_my");
    }

    openPayslip(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.payslip",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("hr_payroll_community_dashboard", HrPayrollDashboard);
