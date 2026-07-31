/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ControlPanel } from "@web/search/control_panel/control_panel";

const HRSD_DASHBOARD_URL = "/hrsd/dashboard";

patch(ControlPanel.prototype, {
    get showHrsdBackButton() {
        return true;
    },

    get hrsdBackTooltip() {
        return _t("Back to HR Dashboard");
    },

    onHrsdBackClick() {
        window.location.href = HRSD_DASHBOARD_URL;
    },
});
