/** @odoo-module **/
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

// Donut chart segments definition (order matters for visual layout)
const CHART_SEGMENTS = [
    { key: "expired",           label: "Expired Docs",   color: "#ef4444" },
    { key: "expiring_30d",      label: "Expiring (30d)", color: "#f97316" },
    { key: "probation_soon",    label: "Probation Due",  color: "#a855f7" },
    { key: "open_disciplinary", label: "Disciplinary",   color: "#22d3ee" },
    { key: "active_loans",      label: "Active Loans",   color: "#4ade80" },
];

export class HRPlusDashboard extends Component {
    static template = "mn_hr_plus.Dashboard";
    static props = {};

    setup() {
        this.state = useState({
            kpis: {},
            expiring: [],
            probation: [],
            loans: [],
            recent_hires: [],
            today_label: new Date().toLocaleDateString("en-US", {
                weekday: "long", year: "numeric", month: "long", day: "numeric",
            }),
        });

        this.alertChartRef = useRef("alertChart");
        this._timer = null;
        this._chartRaf = null;
        this._mounted = false;

        onWillStart(async () => { await this._load(false); });

        onMounted(() => {
            this._mounted = true;
            this._drawDonut();
            this._timer = setInterval(() => this._load(true), 30000);
        });

        onWillUnmount(() => {
            this._mounted = false;
            if (this._timer) clearInterval(this._timer);
            if (this._chartRaf) cancelAnimationFrame(this._chartRaf);
        });
    }

    async _load(redrawChart = true) {
        const r = await rpc("/hr_plus/dashboard", {});
        Object.assign(this.state, r);
        if (redrawChart && this._mounted) {
            // Let OWL flush its render before touching the canvas
            setTimeout(() => this._drawDonut(), 0);
        }
    }

    async refresh() { await this._load(true); }

    openDoc(id) {
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mn.hr.document.tracker",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ── Animated Donut Chart ────────────────────────────────────────────────
    _drawDonut() {
        const canvas = this.alertChartRef.el;
        if (!canvas) return;

        const dpr = window.devicePixelRatio || 1;
        const LOGICAL = 190;

        canvas.width  = LOGICAL * dpr;
        canvas.height = LOGICAL * dpr;
        canvas.style.width  = LOGICAL + "px";
        canvas.style.height = LOGICAL + "px";

        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);

        const kpis = this.state.kpis;
        const segs = CHART_SEGMENTS
            .map(s => ({ ...s, value: kpis[s.key] || 0 }))
            .filter(s => s.value > 0);
        const total = segs.reduce((sum, s) => sum + s.value, 0);

        const cx = LOGICAL / 2;
        const cy = LOGICAL / 2;
        const R  = LOGICAL / 2 - 10;   // outer radius
        const r  = R * 0.58;           // inner radius (donut hole)
        const GAP = segs.length > 1 ? 0.05 : 0; // gap in radians between slices

        if (this._chartRaf) cancelAnimationFrame(this._chartRaf);

        const t0 = performance.now();
        const DURATION = 950;

        const easeOutCubic = t => 1 - Math.pow(1 - t, 3);

        const frame = (now) => {
            const raw  = Math.min((now - t0) / DURATION, 1);
            const ease = easeOutCubic(raw);

            ctx.clearRect(0, 0, LOGICAL, LOGICAL);

            // Background ring
            ctx.beginPath();
            ctx.arc(cx, cy, R, 0, Math.PI * 2);
            ctx.arc(cx, cy, r, 0, Math.PI * 2, true);
            ctx.fillStyle = "rgba(255,255,255,0.04)";
            ctx.fill();

            if (total === 0) {
                // Empty state
                ctx.fillStyle = "#374151";
                ctx.font = "500 13px Inter, system-ui, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText("All Clear ✓", cx, cy);
                return;
            }

            // Draw slices
            let angle = -Math.PI / 2;
            for (const seg of segs) {
                const fullSlice = (seg.value / total) * Math.PI * 2 * ease;
                const sweep = fullSlice - GAP;

                if (sweep > 0) {
                    // Glow effect
                    ctx.shadowColor = seg.color;
                    ctx.shadowBlur  = 10;

                    ctx.beginPath();
                    ctx.arc(cx, cy, R, angle + GAP / 2, angle + sweep + GAP / 2);
                    ctx.arc(cx, cy, r, angle + sweep + GAP / 2, angle + GAP / 2, true);
                    ctx.closePath();
                    ctx.fillStyle = seg.color;
                    ctx.fill();

                    ctx.shadowBlur = 0;
                }
                angle += fullSlice;
            }

            // Centre label (fade in after 70% progress)
            if (ease > 0.7) {
                const alpha = Math.min((ease - 0.7) / 0.3, 1);
                ctx.globalAlpha = alpha;

                ctx.fillStyle = "#f1f5f9";
                ctx.font = "bold 28px Inter, system-ui, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(String(total), cx, cy - 10);

                ctx.fillStyle = "#64748b";
                ctx.font = "500 11px Inter, system-ui, sans-serif";
                ctx.fillText("total alerts", cx, cy + 13);

                ctx.globalAlpha = 1;
            }

            if (raw < 1) {
                this._chartRaf = requestAnimationFrame(frame);
            }
        };

        this._chartRaf = requestAnimationFrame(frame);
    }
}

registry.category("actions").add("mn_hr_plus_dashboard", HRPlusDashboard);
