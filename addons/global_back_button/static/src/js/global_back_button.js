/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";
import { routerBus } from "@web/core/browser/router";

/**
 * Global Back Button - Odoo 19
 *
 * Patches the ControlPanel component to inject a "Back" button
 * whenever the current view is a form view (i.e. a record is open).
 * Navigation history is stored per-session in a simple stack managed
 * by a dedicated service.
 */

// ---------------------------------------------------------------------------
// Navigation History Service
// Keeps a stack of {action, options} pairs so we can pop back correctly.
// ---------------------------------------------------------------------------
export const navigationHistoryService = {
    id: "navigationHistory",
    start() {
        const stack = [];

        return {
            /**
             * Push the current action state before navigating into a record.
             * @param {Object} entry  { actionId, actionTag, resModel, viewType, context, domain }
             */
            push(entry) {
                stack.push(entry);
            },

            /**
             * Pop the last entry and return it (or null if empty).
             * @returns {Object|null}
             */
            pop() {
                return stack.length ? stack.pop() : null;
            },

            /**
             * Peek at the last entry without removing it.
             * @returns {Object|null}
             */
            peek() {
                return stack.length ? stack[stack.length - 1] : null;
            },

            /**
             * Return true when there is at least one entry to go back to.
             */
            canGoBack() {
                return stack.length > 0;
            },

            clear() {
                stack.length = 0;
            },
        };
    },
};

// ---------------------------------------------------------------------------
// ControlPanel patch
// ---------------------------------------------------------------------------
patch(ControlPanel.prototype, {
    setup() {
        super.setup(...arguments);

        this.actionService = useService("action");
        // Router service may not be available in all layouts (e.g. non-SPA contexts).
        // Guard access so the ControlPanel doesn't throw when router is missing.
        try {
            this.router = useService("router");
        } catch (err) {
            this.router = null;
        }

        // Local reactive state: whether the Back button should be visible
        this.backBtnState = useState({ visible: false });

        // We rely on the router's current state to decide visibility.
        // A form view will generally have a `resId` (or `active_id`) in the router state.
        const updateVisibility = () => {
            if (!this.router) {
                this.backBtnState.visible = false;
                return;
            }
            const state = this.router.current;
            // Show the Back button when we are inside a form view
            // (router state contains a resId for single-record views).
            const inFormView = state && (state.resId !== undefined || state.active_id !== undefined);
            this.backBtnState.visible = !!inFormView;
        };

        onMounted(() => {
            if (!this.router) {
                this.backBtnState.visible = false;
                return;
            }
            updateVisibility();
            // Re-evaluate on route changes via the shared routerBus event.
            this._unsubRouter = routerBus.addEventListener("ROUTE_CHANGE", updateVisibility);
        });

        onWillUnmount(() => {
            if (this._unsubRouter) {
                this.router.bus.removeEventListener(
                    "state-pushed",
                    this._unsubRouter
                );
            }
        });
    },

    /**
     * Called when the user clicks the Back button.
     * Uses history.back() for seamless SPA navigation.
     */
    onGlobalBackClick() {
        // history.back() triggers Odoo's router which cleanly restores
        // the previous view (list/kanban/etc.) without a full page reload.
        window.history.back();
    },
});
