import { Component, useState, onWillUpdateProps } from "@odoo/owl";

/**
 * Modern replacement for a native <select>: a search/click input that opens a
 * floating list of options styled consistently across all Document Templates pages.
 *
 * Deliberately duplicated from the `construction` addon's widget of the same name/API
 * rather than imported cross-addon -- this addon must not depend on `construction`.
 */
export class ModernSelect extends Component {
    static template = "document_templates.ModernSelect";
    static props = {
        options: Array,
        value: { optional: true },
        placeholder: { type: String, optional: true },
        emptyLabel: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        searchable: { type: Boolean, optional: true },
        onSelect: Function,
    };
    static defaultProps = {
        placeholder: "Select…",
        emptyLabel: "No matches.",
        disabled: false,
        searchable: true,
    };

    setup() {
        this.state = useState({ query: this.labelFor(this.props.value, this.props.options), open: false });
        onWillUpdateProps((nextProps) => {
            if (!this.state.open) {
                this.state.query = this.labelFor(nextProps.value, nextProps.options);
            }
        });
    }

    labelFor(value, options) {
        if (value === undefined || value === false || value === null || value === "") return "";
        const opt = options.find((o) => String(o.value) === String(value));
        return opt ? opt.label : "";
    }

    get filteredOptions() {
        if (!this.props.searchable) return this.props.options;
        const q = this.state.query.trim().toLowerCase();
        if (!q) return this.props.options;
        return this.props.options.filter((o) => {
            return o.label.toLowerCase().includes(q) || String(o.sublabel || "").toLowerCase().includes(q);
        });
    }

    onInput(ev) {
        this.state.query = ev.target.value;
        this.state.open = true;
        if (this.props.value !== "" && this.props.value !== false && this.props.value != null) {
            this.props.onSelect("");
        }
    }

    toggleOpen() {
        if (!this.props.disabled) this.state.open = !this.state.open;
    }

    onFocus() {
        if (!this.props.disabled) this.state.open = true;
    }

    onBlur() {
        setTimeout(() => { this.state.open = false; }, 150);
    }

    select(opt) {
        this.state.query = opt.label;
        this.state.open = false;
        this.props.onSelect(opt.value);
    }
}
