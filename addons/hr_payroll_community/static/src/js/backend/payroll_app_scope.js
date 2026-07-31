/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

// Toggles a body class only while the Payroll app is active, so the theme
// in payroll_theme.scss never bleeds into other Odoo apps.
const PAYROLL_APP_XMLID = "hr_payroll_community.menu_hr_payroll_community_root";
const BODY_CLASS = "o_app_hr_payroll";

patch(NavBar.prototype, {
    get currentApp() {
        const app = super.currentApp;
        document.body.classList.toggle(BODY_CLASS, app?.xmlid === PAYROLL_APP_XMLID);
        return app;
    },
});
