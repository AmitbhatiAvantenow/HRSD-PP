import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class PreviewDialog extends Component {
    static template = "document_templates.PreviewDialog";
    static components = { Dialog };
    static props = {
        templateId: Number,
        templateName: { type: String, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: true, error: "", pdfBase64: "" });

        onWillStart(async () => {
            try {
                this.state.pdfBase64 = await this.orm.call(
                    "document.template", "preview_pdf_base64", [[this.props.templateId], {}]);
            } catch (e) {
                this.state.error = e.message?.data?.message || "Could not build a preview.";
            } finally {
                this.state.loading = false;
            }
        });
    }

    get pdfDataUrl() {
        return this.state.pdfBase64 ? `data:application/pdf;base64,${this.state.pdfBase64}` : "";
    }

    close() {
        this.props.close();
    }
}
