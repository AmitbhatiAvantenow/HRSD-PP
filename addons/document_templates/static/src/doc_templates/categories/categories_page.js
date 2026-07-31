import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";
import { ModernSelect } from "../widgets/modern_select";

const DEPARTMENT_LABELS = {
    real_estate: "Real Estate", hr: "HR", finance: "Finance", legal: "Legal",
    procurement: "Procurement", sales: "Sales", maintenance: "Maintenance",
    operations: "Operations", administration: "Administration", marketing: "Marketing",
};
const DEPARTMENT_ORDER = Object.keys(DEPARTMENT_LABELS);

export class CategoriesPage extends Component {
    static template = "document_templates.CategoriesPage";
    static components = { DocShell, ModernSelect };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            categories: [],
            adding: false,
            newName: "",
            newDepartment: "real_estate",
        });

        onWillStart(() => this.reload());
    }

    async reload() {
        this.state.categories = await this.orm.searchRead(
            "document.template.category", [], ["name", "department", "template_count", "icon"],
            { order: "sequence, name" });
    }

    get groupedCategories() {
        const byDept = {};
        for (const cat of this.state.categories) {
            (byDept[cat.department] ||= []).push(cat);
        }
        return DEPARTMENT_ORDER.map((key) => ({ key, label: DEPARTMENT_LABELS[key], items: byDept[key] || [] }));
    }

    get departmentOptions() {
        return DEPARTMENT_ORDER.map((key) => ({ value: key, label: DEPARTMENT_LABELS[key] }));
    }

    toggleAdd() {
        this.state.adding = !this.state.adding;
    }

    onDepartmentSelect(v) {
        this.state.newDepartment = v;
    }

    async createCategory() {
        const name = this.state.newName.trim();
        if (!name) return;
        await this.orm.create("document.template.category", [{ name, department: this.state.newDepartment }]);
        this.state.newName = "";
        this.state.adding = false;
        this.reload();
    }
}

registry.category("actions").add("doc_categories", CategoriesPage);
