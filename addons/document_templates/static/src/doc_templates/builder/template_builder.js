import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";
import { ModernSelect } from "../widgets/modern_select";
import { PreviewDialog } from "../templates/preview_dialog";

const PX_PER_PT = 96 / 72;
const PAGE_SIZES_PT = { a4: [595, 842], letter: [612, 792], legal: [612, 1008] };
const MIN_W_PT = 20;
const MIN_H_PT = 12;
const MIN_ZOOM = 0.3;
const MAX_ZOOM = 2;
const ZOOM_STEP = 0.1;

const VARIABLE_TYPES = [
    { value: "text", label: "Text" },
    { value: "long_text", label: "Long Text" },
    { value: "number", label: "Number" },
    { value: "currency", label: "Currency" },
    { value: "date", label: "Date" },
    { value: "boolean", label: "Yes/No" },
];

const PALETTE = [
    { type: "text", label: "Text", icon: "fa-font" },
    { type: "heading", label: "Heading", icon: "fa-header" },
    // Placed 3rd (not buried at the bottom of a 15-item scrolling list) since
    // this is the main way to drop {{ variables }} like Employee Name onto
    // the document -- it needs to be seen without scrolling to be found at all.
    { type: "dynamic_field", label: "Variables", icon: "fa-code", special: true },
    { type: "image", label: "Image", icon: "fa-picture-o" },
    { type: "table", label: "Table", icon: "fa-table" },
    { type: "qr", label: "QR Code", icon: "fa-qrcode" },
    { type: "signature", label: "Signature", icon: "fa-pencil-square-o" },
    { type: "stamp", label: "Stamp", icon: "fa-certificate" },
    { type: "logo", label: "Logo", icon: "fa-building" },
    { type: "divider", label: "Divider", icon: "fa-minus" },
    { type: "icon", label: "Icon", icon: "fa-smile-o" },
    { type: "page_break", label: "Page Break", icon: "fa-scissors" },
    { type: "barcode", label: "Barcode", icon: "fa-barcode" },
    { type: "chart", label: "Chart", icon: "fa-bar-chart" },
    { type: "shape", label: "Shapes", icon: "fa-square-o" },
];

function newBlockId() {
    return `b_${Math.random().toString(36).slice(2, 9)}`;
}

function defaultBlock(type, x, y) {
    const base = { id: newBlockId(), type, x: Math.round(x), y: Math.round(y), z: 1 };
    switch (type) {
        case "text":
            return { ...base, w: 300, h: 24, props: { text: "Text block", font_size: 11, align: "left", bold: false, italic: false, color: "#111111" } };
        case "heading":
            return { ...base, w: 300, h: 34, props: { text: "Heading", level: 1, align: "left", bold: true, color: "#111111" } };
        case "image":
            return { ...base, w: 160, h: 100, props: { image_data: "", fit: "contain" } };
        case "logo":
            return { ...base, w: 100, h: 60, props: { image_data: "", fit: "contain" } };
        case "stamp":
            return { ...base, w: 100, h: 100, props: { image_data: "", fit: "contain" } };
        case "table":
            return { ...base, w: 320, h: 80, props: { headers: ["Column 1", "Column 2"], rows: [["Row 1", "Value"], ["Row 2", "Value"]], font_size: 9 } };
        case "qr":
            return { ...base, w: 80, h: 80, props: { data: "https://example.com" } };
        case "barcode":
            return { ...base, w: 150, h: 50, props: { data: "123456789", format: "code128" } };
        case "divider":
            return { ...base, w: 300, h: 2, props: { color: "#cccccc", style: "solid", thickness: 1 } };
        case "signature":
            return { ...base, w: 200, h: 70, props: { label: "Signature", box_style: "solid" } };
        case "shape":
            return { ...base, w: 100, h: 60, props: { shape: "rectangle", border_color: "#333333", fill_color: "" } };
        case "icon":
            return { ...base, w: 24, h: 24, props: { color: "#4453c9" } };
        case "page_break":
            return { ...base, w: 0, h: 0, z: 0, props: {} };
        case "chart":
            return { ...base, w: 220, h: 100, props: { data: [{ label: "Jan", value: 10 }, { label: "Feb", value: 25 }, { label: "Mar", value: 18 }], color: "#4453c9" } };
        default:
            return { ...base, w: 100, h: 40, props: {} };
    }
}

export class TemplateBuilder extends Component {
    static template = "document_templates.TemplateBuilder";
    static components = { DocShell, ModernSelect };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.canvasRef = useRef("canvas");
        this.palette = PALETTE;
        this.dragState = null;
        this.resizeState = null;

        this.state = useState({
            loading: true,
            saving: false,
            savedFlash: false,
            templateId: null,
            templateName: "",
            paperSize: "a4",
            orientation: "portrait",
            pageWidthPt: 595,
            pageHeightPt: 842,
            page: { header_text: "", footer_text: "", background_color: "" },
            blocks: [],
            selectedId: null,
            variables: [],
            varPopoverOpen: false,
            newVarName: "",
            newVarType: "text",
            newVarRequired: true,
            newVarDefault: "",
            newVarError: "",
            zoom: 1,
            fullscreen: false,
        });
        this.variableTypes = VARIABLE_TYPES;

        onWillStart(async () => {
            const templateId = this.props.action?.context?.default_template_id;
            this.state.templateId = templateId;
            const data = await this.orm.call("document.template", "get_builder_data", [templateId]);
            this.state.templateName = data.template.name;
            this.state.paperSize = data.template.paper_size;
            this.state.orientation = data.template.orientation;
            this.state.pageWidthPt = data.page_width_pt;
            this.state.pageHeightPt = data.page_height_pt;
            this.state.page = { header_text: "", footer_text: "", background_color: "", ...(data.canvas.page || {}) };
            this.state.blocks = (data.canvas.blocks || []).map((b) => ({ ...b, props: { ...(b.props || {}) } }));
            this.state.variables = data.variables;
            this.state.loading = false;
        });

        onMounted(() => window.addEventListener("keydown", this.onKeyDown));
        onWillUnmount(() => window.removeEventListener("keydown", this.onKeyDown));
        this.onKeyDown = this.onKeyDown.bind(this);
    }

    get selectedBlock() {
        return this.state.blocks.find((b) => b.id === this.state.selectedId) || null;
    }

    get canvasStyle() {
        return `width:${this.state.pageWidthPt * PX_PER_PT}px; height:${this.state.pageHeightPt * PX_PER_PT}px;`;
    }

    blockStyle(b) {
        return `left:${b.x * PX_PER_PT}px; top:${b.y * PX_PER_PT}px; width:${Math.max(b.w, 2) * PX_PER_PT}px; height:${Math.max(b.h, 2) * PX_PER_PT}px; z-index:${b.z || 1};`;
    }

    paperSizeOptions() {
        return [{ value: "a4", label: "A4" }, { value: "letter", label: "Letter" }, { value: "legal", label: "Legal" }];
    }
    orientationOptions() {
        return [{ value: "portrait", label: "Portrait" }, { value: "landscape", label: "Landscape" }];
    }

    async onPaperSizeSelect(v) {
        this.state.paperSize = v;
        await this.orm.write("document.template", [this.state.templateId], { paper_size: v });
        this._recomputePageDims();
    }
    async onOrientationSelect(v) {
        this.state.orientation = v;
        await this.orm.write("document.template", [this.state.templateId], { orientation: v });
        this._recomputePageDims();
    }
    _recomputePageDims() {
        const [w, h] = PAGE_SIZES_PT[this.state.paperSize] || PAGE_SIZES_PT.a4;
        const landscape = this.state.orientation === "landscape";
        this.state.pageWidthPt = landscape ? h : w;
        this.state.pageHeightPt = landscape ? w : h;
    }

    zoomIn() {
        this.state.zoom = Math.min(MAX_ZOOM, Math.round((this.state.zoom + ZOOM_STEP) * 100) / 100);
    }
    zoomOut() {
        this.state.zoom = Math.max(MIN_ZOOM, Math.round((this.state.zoom - ZOOM_STEP) * 100) / 100);
    }
    zoomReset() {
        this.state.zoom = 1;
    }

    toggleFullscreen() {
        this.state.fullscreen = !this.state.fullscreen;
    }

    onNameBlur(ev) {
        const name = ev.target.value.trim();
        if (name && name !== this.state.templateName) {
            this.state.templateName = name;
            this.orm.call("document.template", "rename_template", [[this.state.templateId], name]);
        }
    }

    // ------------------------------------------------------------------
    // Palette / drop
    // ------------------------------------------------------------------

    onPaletteDragStart(ev, type) {
        ev.dataTransfer.setData("text/block-type", type);
    }

    // Dragging a variable out of the "Insert Variable" flyout drops a new text
    // block pre-filled with its {{ token }} wherever it's released on the
    // canvas -- the same drop mechanic as every other palette item, since
    // click-to-append-into-the-selected-block alone wasn't discoverable.
    onVariableDragStart(ev, v) {
        ev.dataTransfer.setData("text/block-type", "variable");
        ev.dataTransfer.setData("text/variable-key", v.key);
    }

    onPaletteClick(item) {
        if (item.type === "dynamic_field") {
            this.state.varPopoverOpen = !this.state.varPopoverOpen;
            return;
        }
        // Click-to-add fallback (in addition to drag/drop) -- drops at a fixed offset.
        this._addBlock(item.type, 40, 40);
    }

    onCanvasDrop(ev) {
        const type = ev.dataTransfer.getData("text/block-type");
        if (!type || type === "dynamic_field") return;
        const rect = this.canvasRef.el.getBoundingClientRect();
        const scale = PX_PER_PT * this.state.zoom;
        const x = (ev.clientX - rect.left) / scale;
        const y = (ev.clientY - rect.top) / scale;
        if (type === "variable") {
            const key = ev.dataTransfer.getData("text/variable-key");
            this._addVariableBlock(key, x, y);
            return;
        }
        this._addBlock(type, x, y);
    }

    _addVariableBlock(key, x, y) {
        const block = defaultBlock("text", x, y);
        block.props.text = `{{ ${key} }}`;
        this.state.blocks.push(block);
        this.state.selectedId = block.id;
    }

    _addBlock(type, x, y) {
        const block = defaultBlock(type, x, y);
        this.state.blocks.push(block);
        this.state.selectedId = block.id;
    }

    selectBlock(id) {
        this.state.selectedId = id;
    }

    deleteBlock(id) {
        this.state.blocks = this.state.blocks.filter((b) => b.id !== id);
        if (this.state.selectedId === id) this.state.selectedId = null;
    }

    onKeyDown(ev) {
        if (ev.key === "Escape" && this.state.fullscreen) {
            this.state.fullscreen = false;
            return;
        }
        if (ev.key !== "Delete" && ev.key !== "Backspace") return;
        const tag = (document.activeElement?.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea") return;
        if (this.state.selectedId) {
            this.deleteBlock(this.state.selectedId);
        }
    }

    // ------------------------------------------------------------------
    // Drag / resize (plain Pointer Events, no external DnD library)
    // ------------------------------------------------------------------

    startDrag(ev, block) {
        ev.stopPropagation();
        this.selectBlock(block.id);
        this.dragState = { id: block.id, startX: ev.clientX, startY: ev.clientY, origX: block.x, origY: block.y };
        const onMove = (mev) => {
            if (!this.dragState) return;
            const scale = PX_PER_PT * this.state.zoom;
            const dx = (mev.clientX - this.dragState.startX) / scale;
            const dy = (mev.clientY - this.dragState.startY) / scale;
            const b = this.state.blocks.find((x) => x.id === this.dragState.id);
            if (!b) return;
            b.x = Math.max(0, this.dragState.origX + dx);
            b.y = Math.max(0, this.dragState.origY + dy);
        };
        const onUp = () => {
            this.dragState = null;
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    }

    startResize(ev, block) {
        ev.stopPropagation();
        this.selectBlock(block.id);
        this.resizeState = { id: block.id, startX: ev.clientX, startY: ev.clientY, origW: block.w, origH: block.h };
        const onMove = (mev) => {
            if (!this.resizeState) return;
            const scale = PX_PER_PT * this.state.zoom;
            const dw = (mev.clientX - this.resizeState.startX) / scale;
            const dh = (mev.clientY - this.resizeState.startY) / scale;
            const b = this.state.blocks.find((x) => x.id === this.resizeState.id);
            if (!b) return;
            b.w = Math.max(MIN_W_PT, this.resizeState.origW + dw);
            b.h = Math.max(MIN_H_PT, this.resizeState.origH + dh);
        };
        const onUp = () => {
            this.resizeState = null;
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    }

    // ------------------------------------------------------------------
    // Inspector
    // ------------------------------------------------------------------

    updateGeom(key, ev) {
        const b = this.selectedBlock;
        if (!b) return;
        const v = parseFloat(ev.target.value);
        if (!isNaN(v)) b[key] = v;
    }

    updateProp(key, value) {
        const b = this.selectedBlock;
        if (!b) return;
        b.props[key] = value;
    }

    updatePropFromInput(key, ev) {
        this.updateProp(key, ev.target.value);
    }

    updatePropChecked(key, ev) {
        this.updateProp(key, ev.target.checked);
    }

    updatePropNumber(key, ev) {
        this.updateProp(key, parseFloat(ev.target.value) || 0);
    }

    tableHeadersText(b) {
        return (b.props.headers || []).join(", ");
    }
    onTableHeadersInput(ev) {
        this.updateProp("headers", ev.target.value.split(",").map((s) => s.trim()).filter(Boolean));
    }
    tableRowsText(b) {
        return (b.props.rows || []).map((row) => row.join(", ")).join("\n");
    }
    onTableRowsInput(ev) {
        const rows = ev.target.value.split("\n").filter((l) => l.trim()).map((line) => line.split(",").map((s) => s.trim()));
        this.updateProp("rows", rows);
    }

    async onImageFile(ev, key = "image_data") {
        const file = ev.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => this.updateProp(key, String(reader.result).split(",")[1] || "");
        reader.readAsDataURL(file);
    }

    // ------------------------------------------------------------------
    // Dynamic fields popover
    // ------------------------------------------------------------------

    toggleVarPopover() {
        this.state.varPopoverOpen = !this.state.varPopoverOpen;
    }

    variableTypeLabel(type) {
        return (this.variableTypes.find((t) => t.value === type) || {}).label || type;
    }

    insertVariable(v) {
        const b = this.selectedBlock;
        if (b && (b.type === "text" || b.type === "heading")) {
            b.props.text = `${b.props.text || ""} {{ ${v.key} }}`;
        }
    }

    async createVariable() {
        this.state.newVarError = "";
        const name = this.state.newVarName.trim();
        if (!name) return;
        const key = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
        if (!key) return;
        if (this.state.variables.some((v) => v.key === key)) {
            this.state.newVarError = "A variable with this name already exists on this template.";
            return;
        }
        const vals = {
            template_id: this.state.templateId,
            name,
            key,
            variable_type: this.state.newVarType,
            is_required: this.state.newVarRequired,
            default_value: this.state.newVarDefault || false,
        };
        const id = await this.orm.create("document.template.variable", [vals]);
        this.state.variables.push({
            id: id[0], name, key,
            variable_type: this.state.newVarType,
            default_value: this.state.newVarDefault || "",
            is_required: this.state.newVarRequired,
        });
        this.state.newVarName = "";
        this.state.newVarType = "text";
        this.state.newVarRequired = true;
        this.state.newVarDefault = "";
    }

    async deleteVariable(v, ev) {
        ev.stopPropagation();
        await this.orm.unlink("document.template.variable", [v.id]);
        this.state.variables = this.state.variables.filter((x) => x.id !== v.id);
    }

    // ------------------------------------------------------------------
    // Save / preview
    // ------------------------------------------------------------------

    async save() {
        this.state.saving = true;
        try {
            const canvas = {
                page: this.state.page,
                blocks: this.state.blocks.map((b) => ({
                    id: b.id, type: b.type, x: b.x, y: b.y, w: b.w, h: b.h, z: b.z || 1, props: b.props,
                })),
            };
            await this.orm.call("document.template", "save_canvas", [this.state.templateId, JSON.stringify(canvas)]);
            this.state.savedFlash = true;
            setTimeout(() => { this.state.savedFlash = false; }, 2000);
        } finally {
            this.state.saving = false;
        }
    }

    async preview() {
        await this.save();
        this.dialog.add(PreviewDialog, { templateId: this.state.templateId, templateName: this.state.templateName });
    }
}

registry.category("actions").add("doc_builder", TemplateBuilder);
