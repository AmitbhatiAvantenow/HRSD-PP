/** @odoo-module **/

import { registry } from "@web/core/registry";

// ── 1. Remove "Help" (support) and "My Odoo.com Account" (odoo_account)
//       from the user menu ─────────────────────────────────────────────
const userMenuRegistry = registry.category("user_menuitems");

for (const key of ["support", "odoo_account"]) {
    try {
        if (userMenuRegistry.contains(key)) {
            userMenuRegistry.remove(key);
        }
    } catch {
        // already absent — safe to ignore
    }
}

// ── 2. Remove Activity (mail.activity_menu) and Messages (mail.messaging_menu)
//       from the systray ──────────────────────────────────────────────────────
//       Deferred via Promise so mail's own module registrations have
//       already run before we remove them.
Promise.resolve().then(() => {
    const systrayRegistry = registry.category("systray");
    for (const key of ["mail.activity_menu", "mail.messaging_menu"]) {
        try {
            if (systrayRegistry.contains(key)) {
                systrayRegistry.remove(key);
            }
        } catch {
            // already absent — safe to ignore
        }
    }
});
