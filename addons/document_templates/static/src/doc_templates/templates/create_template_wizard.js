import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ModernSelect } from "../widgets/modern_select";

export class CreateTemplateWizard extends Component {
    static template = "document_templates.CreateTemplateWizard";
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
    get tagOptions() {
        const selected = new Set(this.state.form.tag_ids);
        return this.state.meta.tags
            .filter((t) => !selected.has(String(t.id)))
            .map((t) => ({ value: String(t.id), label: t.name }));
    }
    get selectedTags() {
        return this.state.form.tag_ids
            .map((id) => this.state.meta.tags.find((t) => String(t.id) === String(id)))
            .filter(Boolean);
    }

    onTagSelect(v) {
        if (v && !this.state.form.tag_ids.includes(v)) {
            this.state.form.tag_ids = [...this.state.form.tag_ids, v];
        }
    }
    removeTag(id) {
        this.state.form.tag_ids = this.state.form.tag_ids.filter((t) => t !== String(id));
    }

    get isValid() {
        return !!(this.state.form.name.trim() && this.state.form.category_id);
    }

    onCategorySelect(v) { this.state.form.category_id = v; }
    onLanguageSelect(v) { this.state.form.language = v; }
    onPaperSizeSelect(v) { this.state.form.paper_size = v; }
    onOrientationSelect(v) { this.state.form.orientation = v; }
    onAccessLevelSelect(v) { this.state.form.access_level = v; }

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
            tag_ids: f.tag_ids.map((id) => parseInt(id, 10)),
        };
    }

    async create() {
        if (!this.isValid) return;
        this.state.saving = true;
        this.state.error = "";
        try {
            const result = await this.orm.call("document.template", "create_template_wizard", [this.buildVals()]);
            this.props.onCreated?.(result);
            this.props.close();
        } catch (e) {
            this.state.error = e.message?.data?.message || "Could not create template.";
        } finally {
            this.state.saving = false;
        }
    }

    cancel() {
        this.props.close();
    }
}
