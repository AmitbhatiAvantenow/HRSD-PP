/** @odoo-module **/
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

// Colour palette for recognition donut slices
const REC_COLORS = ["#fbbf24", "#f97316", "#a855f7", "#22d3ee", "#4ade80", "#f87171"];

export class HRPlusEngagement extends Component {
    static template = "mn_hr_plus.Engagement";
    static props = {};

    setup() {
        this.state = useState({
            kpis: {}, recognitions_by_type: [], exit_reasons: [], top_recognised: [],
        });
        this.recChartRef = useRef("recChart");
        this.okrRingRef  = useRef("okrRing");
        this._timer = null;
        this._recRaf = null;
        this._okrRaf = null;
        this._mounted = false;

        onWillStart(async () => { await this._load(false); });
        onMounted(() => {
            this._mounted = true;
            this._drawRecDonut();
            this._drawOkrRing();
            this._timer = setInterval(() => this._load(true), 60000);
        });
        onWillUnmount(() => {
            this._mounted = false;
            if (this._timer) clearInterval(this._timer);
            if (this._recRaf) cancelAnimationFrame(this._recRaf);
            if (this._okrRaf) cancelAnimationFrame(this._okrRaf);
        });
    }

    async _load(redraw = true) {
        const r = await rpc("/hr_plus/dashboard/engagement", {});
        Object.assign(this.state, r);
        if (redraw && this._mounted) {
            setTimeout(() => { this._drawRecDonut(); this._drawOkrRing(); }, 0);
        }
    }

    async refresh() { await this._load(true); }

    barWidth(value, list) {
        const max = Math.max(1, ...list.map(([, v]) => v));
        return Math.round((value / max) * 100) + "%";
    }

    recColor(idx) { return REC_COLORS[idx % REC_COLORS.length]; }

    enpsClass() {
        const v = this.state.kpis.enps || 0;
        return v >= 30 ? "good" : v >= 0 ? "ok" : "bad";
    }

    // ── Recognitions donut ──────────────────────────────────────────────────
    _drawRecDonut() {
        const canvas = this.recChartRef.el;
        if (!canvas) return;

        const dpr = window.devicePixelRatio || 1;
        const L = 150;
        canvas.width  = L * dpr;
        canvas.height = L * dpr;
        canvas.style.width  = L + "px";
        canvas.style.height = L + "px";

        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);

        const segs = this.state.recognitions_by_type
            .map(([label, value], i) => ({ label, value, color: REC_COLORS[i % REC_COLORS.length] }))
            .filter(s => s.value > 0);
        const total = segs.reduce((s, seg) => s + seg.value, 0);

        const cx = L / 2, cy = L / 2, R = L / 2 - 8, r = R * 0.56;
        const GAP = segs.length > 1 ? 0.06 : 0;

        if (this._recRaf) cancelAnimationFrame(this._recRaf);
        const t0 = performance.now(), dur = 900;
        const ease = t => 1 - Math.pow(1 - t, 3);

        const frame = (now) => {
            const p = Math.min((now - t0) / dur, 1);
            const ep = ease(p);

            ctx.clearRect(0, 0, L, L);

            ctx.beginPath();
            ctx.arc(cx, cy, R, 0, Math.PI * 2);
            ctx.arc(cx, cy, r, 0, Math.PI * 2, true);
            ctx.fillStyle = "rgba(255,255,255,0.04)";
            ctx.fill();

            if (total === 0) {
                ctx.fillStyle = "#374151";
                ctx.font = "12px Inter, system-ui, sans-serif";
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

            if (ep > 0.7) {
                const a = Math.min((ep - 0.7) / 0.3, 1);
                ctx.globalAlpha = a;
                ctx.fillStyle = "#f1f5f9";
                ctx.font = "bold 24px Inter, system-ui, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(String(total), cx, cy - 8);
                ctx.fillStyle = "#64748b";
                ctx.font = "10px Inter, system-ui, sans-serif";
                ctx.fillText("total", cx, cy + 12);
                ctx.globalAlpha = 1;
            }

            if (p < 1) this._recRaf = requestAnimationFrame(frame);
        };

        this._recRaf = requestAnimationFrame(frame);
    }

    // ── OKR Progress ring ───────────────────────────────────────────────────
    _drawOkrRing() {
        const canvas = this.okrRingRef.el;
        if (!canvas) return;

        const dpr = window.devicePixelRatio || 1;
        const L = 150;
        canvas.width  = L * dpr;
        canvas.height = L * dpr;
        canvas.style.width  = L + "px";
        canvas.style.height = L + "px";

        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);

        const pct = this.state.kpis.avg_okr_progress || 0;
        const cx = L / 2, cy = L / 2, R = L / 2 - 11, SW = 14;
        const ringColor = pct >= 70 ? "#4ade80" : pct >= 40 ? "#fbbf24" : "#f97316";

        if (this._okrRaf) cancelAnimationFrame(this._okrRaf);
        const t0 = performance.now(), dur = 950;
        const ease = t => 1 - Math.pow(1 - t, 3);

        const frame = (now) => {
            const p = Math.min((now - t0) / dur, 1);
            const ep = ease(p);
            const cur = pct * ep;

            ctx.clearRect(0, 0, L, L);

            ctx.beginPath();
            ctx.arc(cx, cy, R, 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(255,255,255,0.07)";
            ctx.lineWidth = SW;
            ctx.stroke();

            if (cur > 0) {
                const start = -Math.PI / 2;
                ctx.beginPath();
                ctx.arc(cx, cy, R, start, start + (cur / 100) * Math.PI * 2);
                ctx.strokeStyle = ringColor;
                ctx.lineWidth = SW;
                ctx.lineCap = "round";
                ctx.shadowColor = ringColor;
                ctx.shadowBlur  = 12;
                ctx.stroke();
                ctx.shadowBlur = 0;
            }

            if (ep > 0.5) {
                const a = Math.min((ep - 0.5) / 0.5, 1);
                ctx.globalAlpha = a;
                ctx.fillStyle = ringColor;
                ctx.font = "bold 24px Inter, system-ui, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(Math.round(cur) + "%", cx, cy - 8);
                ctx.fillStyle = "#94a3b8";
                ctx.font = "10px Inter, system-ui, sans-serif";
                ctx.fillText("avg progress", cx, cy + 12);
                ctx.globalAlpha = 1;
            }

            if (p < 1) this._okrRaf = requestAnimationFrame(frame);
        };

        this._okrRaf = requestAnimationFrame(frame);
    }
}

registry.category("actions").add("mn_hr_plus_engagement", HRPlusEngagement);
