import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ModernSelect } from "../widgets/modern_select";

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

export class UploadTemplateWizard extends Component {
    static template = "document_templates.UploadTemplateWizard";
    static components = { Dialog, ModernSelect };
    static props = {
        onCreated: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            saving: false,
            error: "",
            meta: { categories: [], languages: [], paper_sizes: [], orientations: [], access_levels: [], tags: [] },
            form: {
                name: "", category_id: "", description: "",
                language: "en", paper_size: "a4", orientation: "portrait",
                access_level: "private", tag_ids: [],
            },
            file: { data: "", name: "" },
        });

        onWillStart(async () => {
            this.state.meta = await this.orm.call("document.template", "get_template_wizard_meta", []);
        });
    }

    get categoryOptions() {
        return this.state.meta.categories.map((c) => ({ value: String(c.id), label: c.name }));
    }
    get languageOptions() {
        return this.state.meta.languages.map((l) => ({ value: l.key, label: l.label }));
    }
    get paperSizeOptions() {
        return this.state.meta.paper_sizes.map((p) => ({ value: p.key, label: p.label }));
    }
    get orientationOptions() {
        return this.state.meta.orientations.map((o) => ({ value: o.key, label: o.label }));
    }
    get accessLevelOptions() {
        return this.state.meta.access_levels.map((a) => ({ value: a.key, label: a.label }));
    }

    onCategorySelect(v) { this.state.form.category_id = v; }
    onLanguageSelect(v) { this.state.form.language = v; }
    onPaperSizeSelect(v) { this.state.form.paper_size = v; }
    onOrientationSelect(v) { this.state.form.orientation = v; }
    onAccessLevelSelect(v) { this.state.form.access_level = v; }

    get isValid() {
        return !!(this.state.form.name.trim() && this.state.form.category_id && this.state.file.data);
    }

    async onFile(ev) {
        const file = ev.target.files[0];
        if (!file) return;
        if (!file.name.toLowerCase().endsWith(".docx")) {
            this.state.error = "Only Word (.docx) files can be uploaded and made editable.";
            this.state.file = { data: "", name: "" };
            return;
        }
        this.state.error = "";
        this.state.file = { data: await fileToBase64(file), name: file.name };
        if (!this.state.form.name.trim()) {
            this.state.form.name = file.name.replace(/\.docx$/i, "");
        }
    }

    clearFile() {
        this.state.file = { data: "", name: "" };
    }

    buildVals() {
        const f = this.state.form;
        return {
            name: f.name.trim(),
            category_id: parseInt(f.category_id, 10),
            description: f.description.trim(),
            language: f.language,
            paper_size: f.paper_size,
            orientation: f.orientation,
            access_level: f.access_level,
            tag_ids: [],
        };
    }

    async create() {
        if (!this.isValid) return;
        this.state.saving = true;
        this.state.error = "";
        try {
            const result = await this.orm.call("document.template", "create_from_upload", [
                this.buildVals(), this.state.file.data, this.state.file.name,
            ]);
            this.props.onCreated?.(result);
            this.props.close();
        } catch (e) {
            this.state.error = e.message?.data?.message || "Could not import this file.";
        } finally {
            this.state.saving = false;
        }
    }

    cancel() {
        this.props.close();
    }
}
