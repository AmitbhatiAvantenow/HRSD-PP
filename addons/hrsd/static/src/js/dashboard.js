/* =========================================================================
   Shivansh HR Portal — HR Dashboard interactions
   ========================================================================= */
(function () {
  "use strict";

  function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  /* ---- small inline icon library used only by the detail view -------- */
  var ICON_PATHS = {
    userPlus: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M22 11h-6"/>',
    userMinus: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="22" y1="11" x2="16" y2="11"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    shieldCheck: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    briefcase: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>',
    logOut: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4"/>',
    trendingUp: '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    award: '<circle cx="12" cy="8" r="6"/><path d="M9 14.5 7 22l5-3 5 3-2-7.5"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    calendarCheck: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="m9 16 2 2 4-4"/>',
    headset: '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3v5Z"/><path d="M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3v5Z"/>',
    fileText: '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2Z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>',
    gift: '<rect x="3" y="8" width="18" height="13" rx="1"/><path d="M12 8v13"/><path d="M19 8a3 3 0 0 0 0-6 4 4 0 0 0-4 4 4 4 0 0 0-4-4 3 3 0 0 0 0 6Z"/>',
    arrowRight: '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/>',
    bot: '<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><path d="M8 16.5h.01" stroke-width="3" stroke-linecap="round"/><path d="M16 16.5h.01" stroke-width="3" stroke-linecap="round"/>',
    scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="3" y1="12" x2="21" y2="12"/>',
    messageCircle: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    chartBar: '<rect x="3" y="12" width="4" height="9" rx="1"/><rect x="10" y="7" width="4" height="14" rx="1"/><rect x="17" y="3" width="4" height="18" rx="1"/>'
  };

  function iconSvg(name, extraAttrs) {
    var inner = ICON_PATHS[name] || "";
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" ' + (extraAttrs || "") + '>' + inner + '</svg>';
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /* ---- detail content for each HR Operations card is no longer hardcoded
          here: it's configured in Odoo under HR Portal > Dashboard Menus
          (hrsd.dashboard.menu / hrsd.dashboard.submenu) and passed down by
          the server as JSON, keyed by menu record id ----------------------- */
  function readEmbeddedJson(elementId) {
    var el = document.getElementById(elementId);
    if (!el) return {};
    try {
      return JSON.parse(el.textContent || "{}");
    } catch (e) {
      return {};
    }
  }

  /* ---- builds the small 4-node circular flow graphic ------------------ */
  function buildDiagram(cards) {
    var nodes = (cards || []).slice(0, 4);
    var positions = [
      { x: 54, y: 54 },   // top-left
      { x: 166, y: 54 },  // top-right
      { x: 166, y: 166 }, // bottom-right
      { x: 54, y: 166 }   // bottom-left
    ];

    var arrows =
      '<path d="M76,32 Q110,4 144,32" fill="none" stroke="#c7d2fe" stroke-width="2.5" stroke-linecap="round" marker-end="url(#hrsdArrowHead)"/>' +
      '<path d="M188,76 Q216,110 188,144" fill="none" stroke="#c7d2fe" stroke-width="2.5" stroke-linecap="round" marker-end="url(#hrsdArrowHead)"/>' +
      '<path d="M144,188 Q110,216 76,188" fill="none" stroke="#c7d2fe" stroke-width="2.5" stroke-linecap="round" marker-end="url(#hrsdArrowHead)"/>' +
      '<path d="M32,144 Q4,110 32,76" fill="none" stroke="#c7d2fe" stroke-width="2.5" stroke-linecap="round" marker-end="url(#hrsdArrowHead)"/>';

    var nodesHtml = nodes.map(function (c, i) {
      var p = positions[i];
      return '<g transform="translate(' + p.x + ',' + p.y + ')">' +
        '<rect x="-22" y="-22" width="44" height="44" rx="12" fill="var(--' + c.color + '-bg)"></rect>' +
        '<g transform="translate(-11,-11) scale(0.92)" stroke="var(--' + c.color + ')" fill="none" ' +
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + ICON_PATHS[c.icon] + '</g>' +
        '</g>';
    }).join("");

    return '<svg viewBox="0 0 220 190" xmlns="http://www.w3.org/2000/svg">' +
      '<defs><marker id="hrsdArrowHead" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">' +
      '<path d="M0,0 L8,4 L0,8 Z" fill="#c7d2fe"/></marker></defs>' +
      arrows +
      '<circle cx="110" cy="110" r="28" fill="var(--indigo-card-bg)"></circle>' +
      '<g transform="translate(98,98) scale(0.92)" stroke="var(--indigo-card)" fill="none" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + ICON_PATHS.user + '</g>' +
      nodesHtml +
      '</svg>';
  }

  onReady(function () {
    var root = document.querySelector(".hrsd-app");
    if (!root) return;

    var dashboardView = root.querySelector("#hrsd-view-dashboard");
    var detailView = root.querySelector("#hrsd-view-detail");
    var breadcrumbCurrent = root.querySelector("#hrsd-detail-breadcrumb-current");
    var detailTitle = root.querySelector("#hrsd-detail-title");
    var detailDesc = root.querySelector("#hrsd-detail-desc");
    var detailGraphic = root.querySelector("#hrsd-detail-graphic");
    var detailGrid = root.querySelector("#hrsd-detail-grid");
    var DETAIL_DATA = readEmbeddedJson("hrsd-dashboard-menu-data");

    /* ---- open / close the detail view --------------------------------- */
    function showDetail(idx) {
      var data = DETAIL_DATA[idx];
      if (!data || !dashboardView || !detailView) return;

      if (breadcrumbCurrent) breadcrumbCurrent.textContent = data.title;
      if (detailTitle) detailTitle.textContent = data.title;
      if (detailDesc) detailDesc.textContent = data.desc;
      if (detailGraphic) detailGraphic.innerHTML = buildDiagram(data.cards);

      if (detailGrid) {
   detailGrid.innerHTML = data.cards.map(function (c) {
  var isLink = c.url && c.url !== '#';
  var tag = isLink ? 'a' : 'div';
  var attrs = isLink
    ? ' href="' + escapeHtml(c.url) + '" target="_self"'
    : '';
  return '<' + tag + attrs + ' class="hrsd-detail-card' + (isLink ? ' is-clickable' : '') + '">' +
    '<div class="hrsd-detail-card-icon is-' + c.color + '">' + iconSvg(c.icon) + '</div>' +
    '<div class="hrsd-detail-card-title">' + escapeHtml(c.title) + '</div>' +
    '<div class="hrsd-detail-card-desc">' + escapeHtml(c.desc) + '</div>' +
    '</' + tag + '>';
}).join("");
      }
      detailGrid.className = "hrsd-detail-grid" + (data.cards.length === 6 ? " cols-6" : "");

      dashboardView.style.display = "none";
      detailView.style.display = "";
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function showDashboard() {
      if (!dashboardView || !detailView) return;
      detailView.style.display = "none";
      dashboardView.style.display = "";
    }

    /* ---- Quick-access cards: open the matching detail view ------------ */
    var opCards = root.querySelectorAll(".hrsd-op-card");
    opCards.forEach(function (card) {
      card.addEventListener("click", function (ev) {
        ev.preventDefault();
        var directUrl = card.getAttribute("data-url");
        if (directUrl) {
          window.location.href = directUrl;
          return;
        }
        var key = parseInt(card.getAttribute("data-key"), 10);
        showDetail(isNaN(key) ? 0 : key);
      });
    });

    /* ---- Back button + breadcrumb: return to the dashboard ------------ */
    root.querySelectorAll('[data-action="go-dashboard"]').forEach(function (el) {
      el.addEventListener("click", function (ev) {
        ev.preventDefault();
        showDashboard();
      });
    });

    /* ---- "View Details" links inside the detail grid (blank for now) -- */
    if (detailGrid) {
      // keep default navigation for valid urls
    }

    /* ---- Top nav: click -> mark active, navigate if it has a url ----- */
    var navLinks = root.querySelectorAll(".hrsd-nav-link");
    navLinks.forEach(function (link) {
      link.addEventListener("click", function (ev) {
        var url = link.getAttribute("data-url");
        navLinks.forEach(function (l) { l.classList.remove("is-active"); });
        link.classList.add("is-active");
        if (url && url !== "#") {
          window.location.href = url;
        } else {
          ev.preventDefault();
        }
      });
    });

    /* ---- Apps grid icon: jump back to the standard Odoo home menu ---- */
    var appsBtn = root.querySelector("[data-action='apps']");
    if (appsBtn) {
      appsBtn.addEventListener("click", function () {
        window.location.href = "/odoo";
      });
    }

    /* ---- User menu: default Odoo-style account dropdown ---------------- */
    var userMenu = root.querySelector(".hrsd-user-menu");
    var userMenuToggle = root.querySelector("[data-action='toggle-user-menu']");
    if (userMenu && userMenuToggle) {
      userMenuToggle.addEventListener("click", function (ev) {
        ev.stopPropagation();
        userMenu.classList.toggle("is-open");
      });
      document.addEventListener("click", function (ev) {
        if (userMenu.classList.contains("is-open") && !userMenu.contains(ev.target)) {
          userMenu.classList.remove("is-open");
        }
      });
      document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") {
          userMenu.classList.remove("is-open");
        }
      });
      var installAppItem = userMenu.querySelector("[data-action='install-app']");
      if (installAppItem) {
        installAppItem.addEventListener("click", function () {
          if (window.hrsdDeferredInstallPrompt) {
            window.hrsdDeferredInstallPrompt.prompt();
          }
          userMenu.classList.remove("is-open");
        });
      }
      window.addEventListener("beforeinstallprompt", function (ev) {
        ev.preventDefault();
        window.hrsdDeferredInstallPrompt = ev;
      });
    }

    /* ---- Live search box: filters quick-access + nav by simple match - */
    var searchInput = root.querySelector(".hrsd-search input");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        var q = searchInput.value.trim().toLowerCase();
        opCards.forEach(function (card) {
          var title = (card.querySelector(".hrsd-op-title") || {}).textContent || "";
          var match = !q || title.toLowerCase().indexOf(q) !== -1;
          card.style.display = match ? "" : "none";
        });
      });
    }

    /* ---- Logout button: route through Odoo's standard logout path ---- */
    var logoutBtn = root.querySelector(".hrsd-logout");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function () {
        window.location.href = "/web/session/logout?redirect=/hrsd/dashboard";
      });
    }
  });
})();