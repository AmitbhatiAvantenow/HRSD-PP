(function () {
    "use strict";

    var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var pointerFine = window.matchMedia && window.matchMedia("(pointer: fine)").matches;

    function setFooterYear() {
        document.querySelectorAll(".o_hrsd_year").forEach(function (el) {
            el.textContent = new Date().getFullYear();
        });
    }

    function staggerDelays() {
        document.querySelectorAll("[data-hrsd-delay]").forEach(function (el) {
            el.style.setProperty("--hrsd-delay", el.getAttribute("data-hrsd-delay") + "s");
        });
    }

    /**
     * Layered mouse parallax: each [data-hrsd-depth] element drifts at its
     * own speed/direction relative to the cursor, plus a slow idle sway,
     * eased with lerp so motion trails smoothly instead of snapping.
     */
    function initParallax() {
        if (reduceMotion || !pointerFine) {
            return;
        }
        var stage = document.querySelector(".o_hrsd_landing, .o_hrsd_login_page");
        if (!stage) {
            return;
        }
        var layers = Array.prototype.slice.call(stage.querySelectorAll("[data-hrsd-depth]"));
        if (!layers.length) {
            return;
        }

        layers.forEach(function (el) {
            el.style.animation = "none";
            el._hrsdDepth = parseFloat(el.getAttribute("data-hrsd-depth")) || 0;
            el._hrsdCurX = 0;
            el._hrsdCurY = 0;
            el._hrsdPhase = Math.random() * Math.PI * 2;
        });

        var targetX = 0;
        var targetY = 0;

        stage.addEventListener("mousemove", function (ev) {
            var rect = stage.getBoundingClientRect();
            targetX = ((ev.clientX - rect.left) / rect.width - 0.5) * 2;
            targetY = ((ev.clientY - rect.top) / rect.height - 0.5) * 2;
        }, { passive: true });

        stage.addEventListener("mouseleave", function () {
            targetX = 0;
            targetY = 0;
        }, { passive: true });

        var start = performance.now();

        function tick(now) {
            var t = (now - start) / 1000;
            layers.forEach(function (el) {
                var depth = el._hrsdDepth;
                var idleX = Math.sin(t * 0.6 + el._hrsdPhase) * depth * 22;
                var idleY = Math.cos(t * 0.5 + el._hrsdPhase) * depth * 16;
                var wantX = targetX * depth * 60 + idleX;
                var wantY = targetY * depth * 60 + idleY;
                el._hrsdCurX += (wantX - el._hrsdCurX) * 0.06;
                el._hrsdCurY += (wantY - el._hrsdCurY) * 0.06;
                el.style.transform = "translate3d(" + el._hrsdCurX.toFixed(2) + "px," + el._hrsdCurY.toFixed(2) + "px,0)";
            });
            requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    /**
     * Scroll-reveal: elements marked [data-hrsd-reveal] fade/slide in once
     * they enter the viewport (used by sections beyond the hero fold).
     */
    function initScrollReveal() {
        var targets = document.querySelectorAll("[data-hrsd-reveal]");
        if (!targets.length) {
            return;
        }
        if (reduceMotion || typeof IntersectionObserver === "undefined") {
            targets.forEach(function (el) { el.classList.add("o_hrsd_in_view"); });
            return;
        }
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("o_hrsd_in_view");
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2, rootMargin: "0px 0px -8% 0px" });
        targets.forEach(function (el) { observer.observe(el); });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setFooterYear();
        staggerDelays();
        initParallax();
        initScrollReveal();
    });
})();
