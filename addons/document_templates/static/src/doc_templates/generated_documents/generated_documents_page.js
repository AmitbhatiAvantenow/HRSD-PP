import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";

const STATUS_CHIP_CLASS = { draft: "doc-c-muted", sent: "doc-c-info", signed: "doc-c-success" };

export class GeneratedDocumentsPage extends Component {
    static template = "document_templates.GeneratedDocumentsPage";
    static components = { DocShell };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ rows: [] });

        onWillStart(() => this.reload());
    }

    async reload() {
        this.state.rows = await this.orm.call("document.generated", "get_generated_documents_data", []);
    }

    statusChipClass(status) {
        return STATUS_CHIP_CLASS[status] || "doc-c-muted";
    }

    async markSent(row) {
        await this.orm.call("document.generated", "action_mark_sent", [[row.id]]);
        this.reload();
    }

    async markSigned(row) {
        await this.orm.call("document.generated", "action_mark_signed", [[row.id]]);
        this.reload();
    }
}

registry.category("actions").add("doc_generated", GeneratedDocumentsPage);
