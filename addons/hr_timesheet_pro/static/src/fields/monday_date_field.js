/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { areDatesEqual } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { useRef, useState, useEffect, onWillRender } from "@odoo/owl";
import { DateTimeField, dateField } from "@web/views/fields/datetime/datetime_field";

const { DateTime } = luxon;

/**
 * Weekly timesheets always run Monday through Sunday, so the "Select Date"
 * (week start) field must only allow Mondays to be picked in the calendar.
 * DateTimeField builds its picker props in a private closure that can't be
 * extended, so this overrides setup() to inject `isDateValid`.
 */
export class MondayDateField extends DateTimeField {
    setup() {
        const getPickerProps = () => {
            const value = this.getRecordValue();
            const pickerProps = {
                value,
                type: this.field.type,
                range: this.isRange(value),
                showRangeToggler:
                    this.relatedField && !this.props.required && !this.props.alwaysRange,
                onToggleRange,
                isDateValid: (date) => date.weekday === 1,
            };
            if (this.props.maxDate) {
                pickerProps.maxDate = this.parseLimitDate(this.props.maxDate);
            }
            if (this.props.minDate) {
                pickerProps.minDate = this.parseLimitDate(this.props.minDate);
            }
            if (!isNaN(this.props.rounding)) {
                pickerProps.rounding = this.props.rounding;
            } else if (this.props.showSeconds) {
                pickerProps.rounding = 0;
            }
            if (this.props.maxPrecision) {
                pickerProps.maxPrecision = this.props.maxPrecision;
            }
            if (this.props.minPrecision) {
                pickerProps.minPrecision = this.props.minPrecision;
            }
            return pickerProps;
        };

        const onToggleRange = () => {
            this.state.range = !this.state.range;
            if (this.state.range) {
                let values = this.values;
                const optionalFieldIndex = values[0] ? 1 : 0;
                if (!values[0] && !values[1]) {
                    values = [DateTime.local(), DateTime.local()];
                }
                values[optionalFieldIndex] = optionalFieldIndex
                    ? values[0].plus({ hours: 1 })
                    : values[1].minus({ hours: 1 });
                this.state.focusedDateIndex = 0;
                this.state.value = values;
            } else {
                const mainFieldIndex = this.props.name === this.startDateField ? 0 : 1;
                this.state.focusedDateIndex = mainFieldIndex;
                this.state.value[mainFieldIndex ? 0 : 1] = false;
            }
        };

        const dateTimePicker = useDateTimePicker({
            target: "root",
            showSeconds: this.props.showSeconds,
            get pickerProps() {
                return getPickerProps();
            },
            onChange: () => {
                this.state.range = this.isRange(this.state.value);
            },
            onClose: () => {
                this.picker.activeInput = "";
            },
            onApply: async () => {
                const toUpdate = {};
                if (Array.isArray(this.state.value)) {
                    [toUpdate[this.startDateField], toUpdate[this.endDateField]] = this.state.value;
                } else {
                    toUpdate[this.props.name] = this.state.value;
                }
                for (const fieldName in toUpdate) {
                    if (areDatesEqual(toUpdate[fieldName], this.props.record.data[fieldName])) {
                        delete toUpdate[fieldName];
                    }
                }
                if (Object.keys(toUpdate).length) {
                    await this.props.record.update(toUpdate);
                }
            },
        });
        this.state = useState(dateTimePicker.state);
        this.picker = useState({ activeInput: "" });
        this.openPicker = dateTimePicker.open;

        this.startDate = useRef("start-date");
        this.endDate = useRef("end-date");

        useEffect(
            () => {
                [this.startDate, this.endDate].forEach((ref, index) => {
                    if (ref.el?.getAttribute("data-field") === this.picker.activeInput) {
                        ref.el.focus();
                        this.openPicker(index);
                    }
                });
            },
            () => [this.startDate.el?.tagName, this.endDate.el?.tagName, this.picker.activeInput]
        );

        onWillRender(() => this.triggerIsDirty());

        this.futureWarningMsg = _t("This date is in the future");
    }
}

registry.category("fields").add("monday_date", {
    ...dateField,
    component: MondayDateField,
});
