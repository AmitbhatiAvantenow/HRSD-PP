/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { browser } from "@web/core/browser/browser";

/**
 * Navbar Back Button
 *
 * Patches the main NavBar component to add a "Go to Home" button right next
 * to the Apps menu (the 9-dot grid icon) / app name. It stays invisible
 * until the app-name area is hovered (see navbar_back_button.scss), then
 * takes you to the Odoo home screen in one click.
 */
patch(NavBar.prototype, {
    onNavbarBackClick() {
        browser.location.href = "/odoo";
    },
});
