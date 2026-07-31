/** @odoo-module **/
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class HRPlusTraining extends Component {
    static template = "mn_hr_plus.Training";
    static props = {};

    setup() {
        this.state = useState({
            kpis: {}, expiring: [], by_category: [], top_learners: [],
        });
        this.complianceRef = useRef("complianceRing");
        this._timer = null;
        this._ringRaf = null;
        this._mounted = false;

        onWillStart(async () => { await this._load(false); });
        onMounted(() => {
            this._mounted = true;
            this._drawComplianceRing();
            this._timer = setInterval(() => this._load(true), 60000);
        });
        onWillUnmount(() => {
            this._mounted = false;
            if (this._timer) clearInterval(this._timer);
            if (this._ringRaf) cancelAnimationFrame(this._ringRaf);
        });
    }

    async _load(redraw = true) {
        const r = await rpc("/hr_plus/dashboard/training", {});
        Object.assign(this.state, r);
        if (redraw && this._mounted) setTimeout(() => this._drawComplianceRing(), 0);
    }

    async refresh() { await this._load(true); }

    barWidth(value, list) {
        const max = Math.max(1, ...list.map(([, v]) => v));
        return Math.round((value / max) * 100) + "%";
    }

    openTraining(id) {
        this.env.services.action.doAction({
            type: "ir.actions.act_window", res_model: "mn.hr.training",
            res_id: id, views: [[false, "form"]], target: "current",
        });
    }

    _drawComplianceRing() {
        const canvas = this.complianceRef.el;
        if (!canvas) return;

        const dpr = window.devicePixelRatio || 1;
        const L = 160;
        canvas.width  = L * dpr;
        canvas.height = L * dpr;
        canvas.style.width  = L + "px";
        canvas.style.height = L + "px";

        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);

        const pct = this.state.kpis.compliance_pct || 0;
        const cx  = L / 2, cy = L / 2;
        const R   = L / 2 - 12;
        const SW  = 16; // stroke width

        const ringColor = pct >= 80 ? "#4ade80" : pct >= 60 ? "#fbbf24" : "#f87171";

        if (this._ringRaf) cancelAnimationFrame(this._ringRaf);
        const t0 = performance.now(), dur = 1000;
        const ease = t => 1 - Math.pow(1 - t, 3);

        const frame = (now) => {
            const p  = Math.min((now - t0) / dur, 1);
            const ep = ease(p);
            const cur = pct * ep;

            ctx.clearRect(0, 0, L, L);

            // Track ring
            ctx.beginPath();
            ctx.arc(cx, cy, R, 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(255,255,255,0.07)";
            ctx.lineWidth = SW;
            ctx.stroke();

            // Progress arc
            if (cur > 0) {
                const start = -Math.PI / 2;
                const end   = start + (cur / 100) * Math.PI * 2;
                ctx.beginPath();
                ctx.arc(cx, cy, R, start, end);
                ctx.strokeStyle = ringColor;
                ctx.lineWidth = SW;
                ctx.lineCap = "round";
                ctx.shadowColor = ringColor;
                ctx.shadowBlur  = 14;
                ctx.stroke();
                ctx.shadowBlur = 0;
            }

            // Centre percentage
            if (ep > 0.5) {
                const alpha = Math.min((ep - 0.5) / 0.5, 1);
                ctx.globalAlpha = alpha;
                ctx.fillStyle = ringColor;
                ctx.font = "bold 26px Inter, system-ui, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(Math.round(cur) + "%", cx, cy - 9);
                ctx.fillStyle = "#94a3b8";
                ctx.font = "500 11px Inter, system-ui, sans-serif";
                ctx.fillText("compliance", cx, cy + 12);
                ctx.globalAlpha = 1;
            }

            if (p < 1) this._ringRaf = requestAnimationFrame(frame);
        };

        this._ringRaf = requestAnimationFrame(frame);
    }
}

registry.category("actions").add("mn_hr_plus_training", HRPlusTraining);
