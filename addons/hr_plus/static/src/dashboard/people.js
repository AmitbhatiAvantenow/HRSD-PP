/** @odoo-module **/
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class HRPlusPeople extends Component {
    static template = "mn_hr_plus.People";
    static props = {};

    setup() {
        this.state = useState({
            kpis: {}, by_dept: [], tenure_buckets: [], age_buckets: [], hires_series: [],
        });
        this.genderChartRef = useRef("genderChart");
        this._timer = null;
        this._chartRaf = null;
        this._mounted = false;

        onWillStart(async () => { await this._load(false); });
        onMounted(() => {
            this._mounted = true;
            this._drawGenderDonut();
            this._timer = setInterval(() => this._load(true), 60000);
        });
        onWillUnmount(() => {
            this._mounted = false;
            if (this._timer) clearInterval(this._timer);
            if (this._chartRaf) cancelAnimationFrame(this._chartRaf);
        });
    }

    async _load(redraw = true) {
        const r = await rpc("/hr_plus/dashboard/people", {});
        Object.assign(this.state, r);
        if (redraw && this._mounted) setTimeout(() => this._drawGenderDonut(), 0);
    }

    async refresh() { await this._load(true); }

    barWidth(value, list) {
        const max = Math.max(1, ...list.map(([, v]) => v));
        return Math.round((value / max) * 100) + "%";
    }

    _drawGenderDonut() {
        const canvas = this.genderChartRef.el;
        if (!canvas) return;

        const dpr = window.devicePixelRatio || 1;
        const L = 170;
        canvas.width  = L * dpr;
        canvas.height = L * dpr;
        canvas.style.width  = L + "px";
        canvas.style.height = L + "px";

        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);

        const male   = this.state.kpis.gender_male   || 0;
        const female = this.state.kpis.gender_female || 0;
        const total  = male + female;

        const segs = [
            { label: "Male",   value: male,   color: "#3b82f6" },
            { label: "Female", value: female, color: "#ec4899" },
        ].filter(s => s.value > 0);

        const cx = L / 2, cy = L / 2;
        const R  = L / 2 - 10;
        const r  = R * 0.58;
        const GAP = segs.length > 1 ? 0.06 : 0;

        if (this._chartRaf) cancelAnimationFrame(this._chartRaf);
        const t0 = performance.now(), dur = 900;
        const ease = t => 1 - Math.pow(1 - t, 3);

        const frame = (now) => {
            const p  = Math.min((now - t0) / dur, 1);
            const ep = ease(p);

            ctx.clearRect(0, 0, L, L);

            // Background ring
            ctx.beginPath();
            ctx.arc(cx, cy, R, 0, Math.PI * 2);
            ctx.arc(cx, cy, r, 0, Math.PI * 2, true);
            ctx.fillStyle = "rgba(255,255,255,0.04)";
            ctx.fill();

            if (total === 0) {
                ctx.fillStyle = "#374151";
                ctx.font = "13px Inter, system-ui, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText("No data", cx, cy);
                return;
            }

            let angle = -Math.PI / 2;
            for (const seg of segs) {
                const slice = (seg.value / total) * Math.PI * 2 * ep;
                const sweep = slice - GAP;
                if (sweep > 0) {
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
                angle += slice;
            }

            // Centre label
            if (ep > 0.7) {
                const a = Math.min((ep - 0.7) / 0.3, 1);
                ctx.globalAlpha = a;
                ctx.fillStyle = "#f1f5f9";
                ctx.font = "bold 26px Inter, system-ui, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(String(total), cx, cy - 9);
                ctx.fillStyle = "#64748b";
                ctx.font = "500 11px Inter, system-ui, sans-serif";
                ctx.fillText("employees", cx, cy + 12);
                ctx.globalAlpha = 1;
            }

            if (p < 1) this._chartRaf = requestAnimationFrame(frame);
        };

        this._chartRaf = requestAnimationFrame(frame);
    }
}

registry.category("actions").add("mn_hr_plus_people", HRPlusPeople);
