import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { loadPDFJSAssets } from "@web/core/utils/pdfjs";
import { Many2One } from "@web/views/fields/many2one/many2one";

const STEPS = [
    { key: "document", label: _t("Template / Upload"), icon: "fa-file-text-o" },
    { key: "customer", label: _t("Choose Customer"), icon: "fa-user" },
    { key: "signers", label: _t("Workflow"), icon: "fa-sitemap" },
    { key: "fields", label: _t("Place Fields"), icon: "fa-object-group" },
    { key: "review", label: _t("Review"), icon: "fa-check" },
];

// Shared props for every partner (Customer) picker in this wizard — search
// as you type against res.partner, with a full "Create and edit..." dialog
// (name/email/phone/company, not just a bare name) for adding a new one.
const PARTNER_PICKER_PROPS = {
    canCreate: true,
    canCreateEdit: true,
    canQuickCreate: false,
    canOpen: true,
    context: { default_customer_rank: 1 },
};

const FIELD_TYPES = [
    { key: "signature", label: _t("Signature"), icon: "fa-pencil-square-o" },
    { key: "initial", label: _t("Initials"), icon: "fa-i-cursor" },
    { key: "name", label: _t("Name"), icon: "fa-user-o" },
    { key: "email", label: _t("Email"), icon: "fa-envelope-o" },
    { key: "phone", label: _t("Phone"), icon: "fa-phone" },
    { key: "company", label: _t("Company"), icon: "fa-building-o" },
    { key: "text", label: _t("Text"), icon: "fa-font" },
    { key: "multiline", label: _t("Multiline"), icon: "fa-align-left" },
    { key: "checkbox", label: _t("Checkbox"), icon: "fa-check-square-o" },
    { key: "radio", label: _t("Radio"), icon: "fa-dot-circle-o" },
    { key: "selection", label: _t("Selection"), icon: "fa-chevron-circle-down" },
    { key: "date", label: _t("Date"), icon: "fa-calendar" },
    { key: "strikethrough", label: _t("Strikethrough"), icon: "fa-strikethrough" },
    { key: "stamp", label: _t("Stamp"), icon: "fa-certificate" },
];

// Cursive style choices for the Signature/Initial preview in "Place Fields" —
// purely a wizard-side preview aid (the signer's actual mark is whatever
// they draw/type/upload on the portal), applied via a CSS custom property.
const SIGNATURE_FONTS = [
    { key: "script1", value: "'Brush Script MT', cursive" },
    { key: "script2", value: "'Lucida Handwriting', 'Segoe Script', cursive" },
    { key: "script3", value: "'Bradley Hand', 'Comic Sans MS', cursive" },
    { key: "script4", value: "'Monotype Corsiva', cursive" },
];

// Default box size (% of page width/height) for a freshly-dropped field.
const FIELD_DEFAULT_SIZE = {
    signature: [18, 6.5], initial: [7, 6], name: [16, 4.5], email: [18, 4.5],
    phone: [14, 4.5], company: [16, 4.5], text: [16, 4.5], multiline: [22, 9],
    checkbox: [3.5, 3.5], radio: [3.5, 3.5], selection: [16, 4.5], date: [12, 4.5],
    strikethrough: [16, 3], stamp: [11, 11],
};

const CATEGORIES = [
    ["offer_letter", _t("Offer Letter")],
    ["contract", _t("Employment Contract")],
    ["nda", _t("NDA / Confidentiality")],
    ["policy", _t("Policy Acknowledgment")],
    ["appraisal", _t("Appraisal Form")],
    ["other", _t("Other")],
];

const AVATAR_COLORS = ["indigo", "violet", "blue", "green", "orange", "pink", "teal"];

export class HrEsignCreateWizard extends Component {
    static template = "hrsd.HrEsignCreateWizard";
    static components = { Many2One };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.steps = STEPS;
        this.categories = CATEGORIES;
        this.fieldTypes = FIELD_TYPES;
        this.signatureFonts = SIGNATURE_FONTS;

        this.state = useState({
            stepIndex: 0,
            templates: [],
            partnerId: false,
            partnerName: "",
            partnerEmail: "",
            title: "",
            category: "other",
            useTemplate: false,
            templateId: false,
            fileName: "",
            fileData: false,
            aiSuggestion: null,
            analyzing: false,
            signers: [],
            workflowType: "parallel",
            dueDate: "",
            priority: "0",
            submitting: false,
            error: "",
            // Signing-request email (Review step)
            emailSubject: "",
            emailMessage: "",
            ccEmails: "",
            // Field placement (drag & drop) step
            fields: [],
            activeSignerIndex: 0,
            pdfPages: [],
            pdfLoading: false,
            pdfError: "",
            templateFileCache: null,
            signatureFont: SIGNATURE_FONTS[0].value,
        });

        onWillStart(async () => {
            this.state.templates = await this.orm.searchRead("hr.esign.template", [], ["id", "name", "category"], { limit: 100 });
        });
    }

    get currentStep() { return this.steps[this.state.stepIndex].key; }
    get isFirstStep() { return this.state.stepIndex === 0; }
    get isLastStep() { return this.state.stepIndex === this.steps.length - 1; }
    get selectedTemplate() { return this.state.templates.find((t) => t.id === this.state.templateId); }
    get progressPct() { return Math.round(((this.state.stepIndex + 1) / this.steps.length) * 100); }

    // Props for the "Choose Customer" step's main picker.
    get customerPickerProps() {
        return {
            ...PARTNER_PICKER_PROPS,
            relation: "res.partner",
            value: this.state.partnerId ? { id: this.state.partnerId, display_name: this.state.partnerName } : false,
            update: (v) => this.onSelectPartner(v),
            domain: () => [],
            placeholder: _t("Search or create a customer…"),
            string: _t("Customer"),
        };
    }

    // Props for a given signer row's picker in the Workflow step.
    signerPartnerPickerProps(index, signer) {
        return {
            ...PARTNER_PICKER_PROPS,
            relation: "res.partner",
            value: signer.partner_id ? { id: signer.partner_id, display_name: signer.name } : false,
            update: (v) => this.onSignerPartnerChange(index, v),
            domain: () => [],
            placeholder: _t("Search or create a customer…"),
            string: _t("Customer"),
        };
    }

    canProceed() {
        const step = this.currentStep;
        if (step === "customer") return !!this.state.partnerId;
        if (step === "document") {
            return !!this.state.title && (this.state.useTemplate ? !!this.state.templateId : !!this.state.fileData);
        }
        if (step === "signers") return this.state.signers.length > 0 && this.state.signers.every((s) => s.name && s.email);
        return true;
    }

    goToStep(index) {
        if (index > this.state.stepIndex) return;
        this.state.stepIndex = index;
        if (this.steps[index].key === "fields") this.loadPdfPreview();
    }

    goNext() {
        if (!this.canProceed()) {
            this.state.error = _t("Please complete this step before continuing.");
            return;
        }
        this.state.error = "";
        if (!this.isLastStep) this.state.stepIndex++;
        if (this.currentStep === "fields") this.loadPdfPreview();
        if (this.currentStep === "review" && !this.state.emailSubject) {
            this.state.emailSubject = `${_t("Signature Request")} - ${this.state.title}`;
        }
    }

    goBack() {
        this.state.error = "";
        if (!this.isFirstStep) this.state.stepIndex--;
    }

    async onSelectPartner(idNamePair) {
        if (!idNamePair) {
            this.state.partnerId = false;
            this.state.partnerName = "";
            this.state.partnerEmail = "";
            return;
        }
        this.state.partnerId = idNamePair.id;
        this.state.partnerName = idNamePair.display_name;
        const [partner] = await this.orm.read("res.partner", [idNamePair.id], ["email"]);
        this.state.partnerEmail = (partner && partner.email) || "";
        if (!this.state.signers.length) {
            this.state.signers.push({ partner_id: this.state.partnerId, name: this.state.partnerName, email: this.state.partnerEmail });
        }
    }

    setUseTemplate(value) {
        this.state.useTemplate = value;
        this.state.error = "";
        this.state.pdfPages = [];
        this.state.fields = [];
    }

    selectTemplate(id) {
        this.state.templateId = id;
        this.state.pdfPages = [];
        this.state.fields = [];
    }

    async onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;
        this.state.fileName = file.name;
        this.state.pdfPages = [];
        this.state.fields = [];
        const reader = new FileReader();
        reader.onload = async () => {
            const b64 = String(reader.result).split(",")[1];
            this.state.fileData = b64;
            if (!this.state.title) this.state.title = file.name.replace(/\.[^.]+$/, "");
            this.state.analyzing = true;
            try {
                const result = await this.orm.call("hr.esign.document", "ai_analyze_file", [b64, file.name]);
                this.state.aiSuggestion = result;
                if (result.suggested_category) this.state.category = result.suggested_category;
            } catch {
                // Best-effort AI analysis — a failure here shouldn't block document creation.
            }
            this.state.analyzing = false;
        };
        reader.readAsDataURL(file);
    }

    addSigner() {
        this.state.signers.push({ partner_id: false, name: "", email: "" });
        this.state.activeSignerIndex = this.state.signers.length - 1;
    }

    removeSigner(index) {
        this.state.signers.splice(index, 1);
        this.state.fields = this.state.fields
            .filter((f) => f.signerIndex !== index)
            .map((f) => (f.signerIndex > index ? { ...f, signerIndex: f.signerIndex - 1 } : f));
        if (this.state.activeSignerIndex >= this.state.signers.length) {
            this.state.activeSignerIndex = Math.max(0, this.state.signers.length - 1);
        }
    }

    setActiveSigner(index) {
        this.state.activeSignerIndex = index;
    }

    signerColor(index) {
        return AVATAR_COLORS[index % AVATAR_COLORS.length];
    }

    fieldTypeMeta(key) {
        return this.fieldTypes.find((f) => f.key === key) || { label: key, icon: "fa-square-o" };
    }

    fieldsOnPage(pageNumber) {
        return this.state.fields.filter((f) => f.page === pageNumber);
    }

    isSignatureType(fieldType) {
        return fieldType === "signature" || fieldType === "initial";
    }

    setSignatureFont(value) {
        this.state.signatureFont = value;
    }

    // What a placed Signature/Initial box shows — the actual signer's name
    // once known, otherwise "Signer N" — so it's never an anonymous box.
    signerLabel(index) {
        const signer = this.state.signers[index];
        return (signer && signer.name) || `${_t("Signer")} ${index + 1}`;
    }

    // -------------------------------------------------------------------
    // Place Fields step — PDF rendering + drag & drop field placement
    // -------------------------------------------------------------------
    async _getFileForPdf() {
        if (!this.state.useTemplate) {
            return { data: this.state.fileData, name: this.state.fileName };
        }
        if (!this.state.templateId) return { data: false, name: "" };
        if (this.state.templateFileCache && this.state.templateFileCache.id === this.state.templateId) {
            return this.state.templateFileCache;
        }
        const [tmpl] = await this.orm.read("hr.esign.template", [this.state.templateId], ["file_data", "file_name"]);
        const cache = { id: this.state.templateId, data: tmpl.file_data, name: tmpl.file_name };
        this.state.templateFileCache = cache;
        return cache;
    }

    async loadPdfPreview() {
        if (this.state.pdfPages.length || this.state.pdfLoading) return;
        this.state.pdfLoading = true;
        this.state.pdfError = "";
        try {
            const { data, name } = await this._getFileForPdf();
            if (!data || !/\.pdf$/i.test(name || "")) {
                this.state.pdfError = _t(
                    "Live preview is only available for PDF documents. You can still send this document — fields just won't be pre-positioned."
                );
                return;
            }
            await loadPDFJSAssets();
            // Force usage of the worker script (avoids the tab hanging on getDocument).
            window.pdfjsLib.GlobalWorkerOptions.workerSrc = "/web/static/lib/pdfjs/build/pdf.worker.js";
            const bytes = Uint8Array.from(atob(data), (c) => c.charCodeAt(0));
            const pdf = await window.pdfjsLib.getDocument({ data: bytes }).promise;
            const pages = [];
            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const viewport = page.getViewport({ scale: 1.4 });
                const canvas = document.createElement("canvas");
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
                pages.push({ url: canvas.toDataURL("image/png") });
            }
            this.state.pdfPages = pages;
        } catch {
            this.state.pdfError = _t("Could not render the document preview.");
        } finally {
            this.state.pdfLoading = false;
        }
    }

    onPaletteDragStart(ev, fieldType) {
        ev.dataTransfer.setData("text/plain", fieldType);
        ev.dataTransfer.effectAllowed = "copy";
    }

    onPageDrop(ev, pageNumber) {
        ev.preventDefault();
        const fieldType = ev.dataTransfer.getData("text/plain");
        if (!fieldType) return;
        // One signature slot and one initials slot per signer — matches how
        // signing actually works (a person has one signature, reused
        // wherever it's placed for them), so dropping a second one for the
        // same signer would just create a box that can never be told apart.
        if (
            this.isSignatureType(fieldType) &&
            this.state.fields.some((f) => f.signerIndex === this.state.activeSignerIndex && f.field_type === fieldType)
        ) {
            const typeLabel = fieldType === "initial" ? _t("Initials") : _t("Signature");
            this.notification.add(
                _t("%s already has a %s field — drag the existing one to move it instead of adding another.", this.signerLabel(this.state.activeSignerIndex), typeLabel),
                { type: "warning" }
            );
            return;
        }
        const rect = ev.currentTarget.getBoundingClientRect();
        const [dw, dh] = FIELD_DEFAULT_SIZE[fieldType] || [16, 4.5];
        let x = ((ev.clientX - rect.left) / rect.width) * 100 - dw / 2;
        let y = ((ev.clientY - rect.top) / rect.height) * 100 - dh / 2;
        x = Math.max(0, Math.min(100 - dw, x));
        y = Math.max(0, Math.min(100 - dh, y));
        this.state.fields.push({
            id: `f${Date.now()}${Math.random().toString(36).slice(2, 7)}`,
            field_type: fieldType,
            page: pageNumber,
            x, y, w: dw, h: dh,
            signerIndex: this.state.activeSignerIndex,
        });
    }

    onFieldMouseDown(ev, field) {
        if (ev.button !== 0) return;
        ev.preventDefault();
        ev.stopPropagation();
        const pageEl = ev.currentTarget.closest(".ohw-pdf-page");
        const rect = pageEl.getBoundingClientRect();
        const startX = ev.clientX;
        const startY = ev.clientY;
        const origX = field.x;
        const origY = field.y;
        const onMove = (mv) => {
            const dx = ((mv.clientX - startX) / rect.width) * 100;
            const dy = ((mv.clientY - startY) / rect.height) * 100;
            field.x = Math.max(0, Math.min(100 - field.w, origX + dx));
            field.y = Math.max(0, Math.min(100 - field.h, origY + dy));
        };
        const onUp = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
        };
        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    onFieldResizeStart(ev, field) {
        if (ev.button !== 0) return;
        ev.preventDefault();
        ev.stopPropagation();
        const pageEl = ev.currentTarget.closest(".ohw-pdf-page");
        const rect = pageEl.getBoundingClientRect();
        const startX = ev.clientX;
        const startY = ev.clientY;
        const origW = field.w;
        const origH = field.h;
        const onMove = (mv) => {
            const dw = ((mv.clientX - startX) / rect.width) * 100;
            const dh = ((mv.clientY - startY) / rect.height) * 100;
            field.w = Math.max(3, Math.min(100 - field.x, origW + dw));
            field.h = Math.max(3, Math.min(100 - field.y, origH + dh));
        };
        const onUp = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
        };
        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    removeField(fieldId) {
        const idx = this.state.fields.findIndex((f) => f.id === fieldId);
        if (idx !== -1) this.state.fields.splice(idx, 1);
    }

    async onSignerPartnerChange(index, idNamePair) {
        if (!idNamePair) {
            this.state.signers[index].partner_id = false;
            return;
        }
        this.state.signers[index].partner_id = idNamePair.id;
        this.state.signers[index].name = idNamePair.display_name;
        const [partner] = await this.orm.read("res.partner", [idNamePair.id], ["email"]);
        this.state.signers[index].email = (partner && partner.email) || "";
    }

    categoryLabel(key) {
        const found = this.categories.find((c) => c[0] === key);
        return found ? found[1] : key;
    }

    avatarColor(id) {
        return AVATAR_COLORS[Math.abs(id || 0) % AVATAR_COLORS.length];
    }

    async onSubmit(sendNow) {
        this.state.submitting = true;
        this.state.error = "";
        try {
            const vals = {
                name: this.state.title,
                category: this.state.category,
                partner_id: this.state.partnerId,
                workflow_type: this.state.workflowType,
                priority: this.state.priority,
                due_date: this.state.dueDate || false,
                email_subject: this.state.emailSubject || false,
                email_message: this.state.emailMessage || false,
                cc_emails: this.state.ccEmails || false,
            };
            if (this.state.useTemplate && this.state.templateId) {
                const { data, name } = await this._getFileForPdf();
                vals.file_data = data;
                vals.file_name = name;
                vals.template_id = this.state.templateId;
            } else {
                vals.file_data = this.state.fileData;
                vals.file_name = this.state.fileName;
            }
            const docId = await this.orm.create("hr.esign.document", [vals]);
            const signerVals = this.state.signers.map((s, i) => ({
                document_id: docId[0],
                partner_id: s.partner_id || false,
                name: s.name,
                email: s.email,
                sequence: (i + 1) * 10,
            }));
            const signerIds = await this.orm.create("hr.esign.signer", signerVals);

            if (this.state.fields.length) {
                const fieldVals = this.state.fields.map((f) => ({
                    document_id: docId[0],
                    signer_id: signerIds[f.signerIndex] || signerIds[0],
                    field_type: f.field_type,
                    page: f.page,
                    pos_x: f.x,
                    pos_y: f.y,
                    width: f.w,
                    height: f.h,
                }));
                await this.orm.create("hr.esign.field", fieldVals);
            }

            if (sendNow) {
                await this.orm.call("hr.esign.document", "action_send", [docId]);
                this.notification.add(_t("Document sent for signature."), { type: "success" });
            } else {
                this.notification.add(_t("Draft saved."), { type: "success" });
            }
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "hr.esign.document",
                res_id: docId[0],
                views: [[false, "form"]],
                target: "current",
            });
        } catch (e) {
            this.state.error = (e && e.message && e.message.data && e.message.data.message) || _t("Something went wrong while creating the document.");
        } finally {
            this.state.submitting = false;
        }
    }

    onCancel() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("hr_esign_create_wizard", HrEsignCreateWizard);
