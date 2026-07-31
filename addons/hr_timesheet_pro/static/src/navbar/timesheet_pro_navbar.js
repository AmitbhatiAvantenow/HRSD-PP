/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

// Toggles a body class only while the Timesheet Pro app is active, so the
// dark navy shell in timesheet_pro_navbar.scss / timesheet_pro_sidebar.scss
// never bleeds into other Odoo apps. Mirrors the pattern already used in
// hr_payroll_community/static/src/js/backend/payroll_app_scope.js.
const ROOT_XMLID = "hr_timesheet_pro.menu_hr_timesheet_pro_root";
const BODY_CLASS = "o_app_htp";

patch(NavBar.prototype, {
    get currentApp() {
        const app = super.currentApp;
        document.body.classList.toggle(BODY_CLASS, app?.xmlid === ROOT_XMLID);
        return app;
    },
});
