/* =========================================================================
   AvanteNow HR Portal — Recruitment Requirements dashboard interactions
   ========================================================================= */
(function () {
  "use strict";

  function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  var STATUS_COLORS = {
    not_started: "blue",
    in_progress: "orange",
    to_deploy: "purple",
    deployed: "green",
    completed: "indigo",
    cancelled: "red",
  };

  var STAT_ICON_COLORS = ["is-blue", "is-green", "is-orange", "is-purple"];

  var ICONS = {
    monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><line x1="8" y1="20" x2="16" y2="20"/><line x1="12" y1="16" x2="12" y2="20"/>',
    filter: '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    userCheck: '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="17 11 19 13 23 9"/>',
    check: '<polyline points="20 6 9 17 4 12"/>',
    building: '<rect x="4" y="2" width="16" height="20" rx="1"/><line x1="9" y1="7" x2="9" y2="7"/><line x1="15" y1="7" x2="15" y2="7"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>',
    trendingUp: '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>',
    dollar: '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    paperclip: '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
    edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z"/>',
    chevronRight: '<polyline points="9 18 15 12 9 6"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    fileCheck: '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2Z"/><polyline points="14 2 14 8 20 8"/><path d="m9 15 2 2 4-4"/>',
    moreVertical: '<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>',
    eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z"/><circle cx="12" cy="12" r="3"/>',
    trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    arrowLeft: '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  };

  function svg(name, extra) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ' + (extra || '') + '>' + (ICONS[name] || '') + '</svg>';
  }

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function $(id) { return document.getElementById(id); }

  function postJSON(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) { return r.json(); });
  }

  function getJSON(url) {
    return fetch(url).then(function (r) { return r.json(); });
  }

  onReady(function () {
    var root = document.querySelector(".rrq-shell");
    if (!root) return;

    var pageData = JSON.parse($("rrq-page-data").textContent || "{}");

    var CLIENT_NAMES = (pageData.clients || []).map(function (c) { return c.name; });
    var EMPLOYEE_NAMES = (pageData.employees || []).map(function (e) { return e.name; });

    function addKnownName(list, name) {
      name = (name || "").trim();
      if (!name) return;
      if (list.indexOf(name) === -1) list.push(name);
    }

    /* ================================================================
       Typeahead (custom dropdown — native <datalist> popups are
       unreliable inside position:fixed modals in some browsers)
       ================================================================ */
    function initTypeahead(inputId, listId, getItems) {
      var input = $(inputId);
      var panel = $(listId);
      if (!input || !panel) return;

      function renderOptions() {
        var q = input.value.trim().toLowerCase();
        var items = getItems();
        var filtered = q ? items.filter(function (n) { return n.toLowerCase().indexOf(q) !== -1; }) : items;
        if (!filtered.length) {
          panel.classList.remove("is-open");
          panel.innerHTML = "";
          return;
        }
        panel.innerHTML = filtered.slice(0, 50).map(function (n) {
          return '<button type="button" class="rrq-typeahead-item">' + escapeHtml(n) + '</button>';
        }).join("");
        panel.classList.add("is-open");
        panel.querySelectorAll(".rrq-typeahead-item").forEach(function (btn) {
          btn.addEventListener("mousedown", function (ev) {
            ev.preventDefault();
            input.value = btn.textContent;
            panel.classList.remove("is-open");
          });
        });
      }

      input.addEventListener("focus", renderOptions);
      input.addEventListener("input", renderOptions);
      input.addEventListener("blur", function () {
        setTimeout(function () { panel.classList.remove("is-open"); }, 150);
      });
    }

    initTypeahead("rrq-form-client-name", "rrq-form-client-name-list", function () { return CLIENT_NAMES; });
    initTypeahead("rrq-form-coordinator", "rrq-form-coordinator-list", function () { return EMPLOYEE_NAMES; });
    initTypeahead("rrq-form-requestor", "rrq-form-requestor-list", function () { return EMPLOYEE_NAMES; });
    initTypeahead("rrq-form-assigned-to", "rrq-form-assigned-to-list", function () { return EMPLOYEE_NAMES; });
    initTypeahead("rrq-candidate-coordinator", "rrq-candidate-coordinator-list", function () { return EMPLOYEE_NAMES; });

    var state = {
      status: pageData.status || "all",
      search: "",
      page: pageData.page || 1,
      pageSize: pageData.page_size || 6,
      detailId: null,
      detailTab: "details",
    };

    /* ================================================================
       Stat cards
       ================================================================ */
    function renderStats(stats) {
      var cards = [
        { icon: "monitor", value: stats.total, label: "Total Requirements", color: "is-blue" },
        { icon: "filter", value: stats.internal_screening, label: "Internal Screening", color: "is-green" },
        { icon: "userCheck", value: stats.interviews, label: "Interviews", color: "is-orange" },
        { icon: "check", value: stats.placed, label: "Placed", color: "is-purple" },
      ];
      $("rrq-stats").innerHTML = cards.map(function (c) {
        return '<div class="rrq-stat-card ' + c.color + '">' +
          '<div class="rrq-stat-icon">' + svg(c.icon) + '</div>' +
          '<div class="rrq-stat-value">' + c.value + '</div>' +
          '<div class="rrq-stat-label">' + c.label + '</div>' +
          '</div>';
      }).join("");
    }

    /* ================================================================
       Status tabs
       ================================================================ */
    function renderTabs() {
      $("rrq-tabs").innerHTML = pageData.status_tabs.map(function (t) {
        var active = t[0] === state.status ? " is-active" : "";
        return '<button type="button" class="rrq-tab-btn' + active + '" data-status="' + t[0] + '">' + escapeHtml(t[1]) + '</button>';
      }).join("");

      root.querySelectorAll(".rrq-tab-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
          state.status = btn.getAttribute("data-status");
          state.page = 1;
          renderTabs();
          loadList();
        });
      });
    }

    /* ================================================================
       Requirement cards + pagination
       ================================================================ */
    function buildRequirementCard(r) {
      return '<div class="rrq-req-card is-' + r.priority_color + '" data-id="' + r.id + '">' +
        '<div class="rrq-req-top">' +
          '<div class="rrq-req-top-left">' +
            '<div class="rrq-req-avatar is-' + r.avatar_color + '">' + escapeHtml(r.avatar_initials) + '</div>' +
            '<div>' +
              '<div class="rrq-req-code">' + escapeHtml(r.code) + '</div>' +
              '<div class="rrq-req-priority is-' + r.priority_color + '">' + escapeHtml(r.priority_label.toUpperCase()) + '</div>' +
            '</div>' +
          '</div>' +
          '<span class="rrq-status-badge is-' + (STATUS_COLORS[r.status] || 'blue') + '">' + escapeHtml(r.status_label) + '</span>' +
        '</div>' +
        '<div class="rrq-req-title">' + escapeHtml(r.job_title) + '</div>' +
        '<div class="rrq-req-client">' + svg("building") + '<span>' + escapeHtml(r.client_name) + '</span></div>' +
        '<div class="rrq-req-desc">' + escapeHtml(r.job_description) + '</div>' +
        '<div class="rrq-req-footer">' +
          '<div class="rrq-req-footer-left">' +
            '<div class="rrq-req-footer-item">' + svg("users") + '<span>' + r.candidate_count + ' candidates</span></div>' +
            '<div class="rrq-req-footer-item">' + svg("calendar") + '<span>' + escapeHtml(r.open_date) + '</span></div>' +
          '</div>' +
          '<div class="rrq-card-menu-wrap">' +
            '<button type="button" class="rrq-icon-btn-sm rrq-card-menu-btn" data-action="toggle-card-menu">' + svg("moreVertical") + '</button>' +
            '<div class="rrq-card-menu">' +
              '<button type="button" class="rrq-card-menu-item" data-menu-action="view" data-id="' + r.id + '">' + svg("eye") + 'View Details</button>' +
              '<button type="button" class="rrq-card-menu-item" data-menu-action="edit" data-id="' + r.id + '">' + svg("edit") + 'Edit</button>' +
              '<button type="button" class="rrq-card-menu-item is-danger" data-menu-action="delete" data-id="' + r.id + '">' + svg("trash") + 'Delete</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';
    }

    function renderPagination(total, page, pageSize) {
      var totalPages = Math.max(1, Math.ceil(total / pageSize));
      var from = total === 0 ? 0 : (page - 1) * pageSize + 1;
      var to = Math.min(total, page * pageSize);
      $("rrq-pagination-info").textContent = "Showing " + from + " to " + to + " of " + total + " requirements";

      var buttons = [];
      buttons.push('<button type="button" class="rrq-page-btn" data-page="1" ' + (page <= 1 ? 'disabled="disabled"' : '') + '>&laquo;</button>');
      buttons.push('<button type="button" class="rrq-page-btn" data-page="' + (page - 1) + '" ' + (page <= 1 ? 'disabled="disabled"' : '') + '>&lsaquo;</button>');
      for (var p = 1; p <= totalPages; p++) {
        buttons.push('<button type="button" class="rrq-page-btn' + (p === page ? ' is-active' : '') + '" data-page="' + p + '">' + p + '</button>');
      }
      buttons.push('<button type="button" class="rrq-page-btn" data-page="' + (page + 1) + '" ' + (page >= totalPages ? 'disabled="disabled"' : '') + '>&rsaquo;</button>');
      buttons.push('<button type="button" class="rrq-page-btn" data-page="' + totalPages + '" ' + (page >= totalPages ? 'disabled="disabled"' : '') + '>&raquo;</button>');
      $("rrq-pagination-controls").innerHTML = buttons.join("");

      root.querySelectorAll("#rrq-pagination-controls .rrq-page-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
          if (btn.disabled) return;
          state.page = parseInt(btn.getAttribute("data-page"), 10);
          loadList();
        });
      });
    }

    function renderList(data) {
      var grid = $("rrq-grid");
      var empty = $("rrq-empty");
      if (!data.requirements.length) {
        grid.innerHTML = "";
        empty.style.display = "";
      } else {
        empty.style.display = "none";
        grid.innerHTML = data.requirements.map(buildRequirementCard).join("");
        grid.querySelectorAll(".rrq-req-card").forEach(function (card) {
          card.addEventListener("click", function () {
            openDetailModal(parseInt(card.getAttribute("data-id"), 10));
          });
        });
        grid.querySelectorAll('[data-action="toggle-card-menu"]').forEach(function (btn) {
          btn.addEventListener("click", function (ev) {
            ev.stopPropagation();
            var menu = btn.nextElementSibling;
            var isOpen = menu.classList.contains("is-open");
            closeAllCardMenus();
            if (!isOpen) menu.classList.add("is-open");
          });
        });
        grid.querySelectorAll("[data-menu-action]").forEach(function (btn) {
          btn.addEventListener("click", function (ev) {
            ev.stopPropagation();
            closeAllCardMenus();
            var id = parseInt(btn.getAttribute("data-id"), 10);
            var action = btn.getAttribute("data-menu-action");
            if (action === "view") openDetailModal(id);
            else if (action === "edit") editRequirementById(id);
            else if (action === "delete") deleteRequirement(id);
          });
        });
      }
      renderPagination(data.total, data.page, data.page_size);
    }

    function closeAllCardMenus() {
      root.querySelectorAll(".rrq-card-menu.is-open").forEach(function (m) { m.classList.remove("is-open"); });
    }
    document.addEventListener("click", closeAllCardMenus);

    function editRequirementById(id) {
      getJSON("/hrsd/recruitment/requirements/detail?id=" + id).then(function (data) {
        if (!data.ok) return;
        openFormModal(data.requirement.form);
      });
    }

    function deleteRequirement(id) {
      if (!window.confirm("Delete this requirement? This cannot be undone.")) return;
      postJSON("/hrsd/recruitment/requirements/delete", { id: id }).then(function (data) {
        if (!data.ok) return;
        loadList();
      });
    }

    function loadList() {
      postJSON("/hrsd/recruitment/requirements/list", {
        status: state.status, search: state.search, page: state.page,
      }).then(function (data) {
        if (!data.ok) return;
        renderStats(data.stats);
        renderList(data);
      });
    }

    /* ================================================================
       Search
       ================================================================ */
    var searchTimer = null;
    $("rrq-search-input").addEventListener("input", function (ev) {
      clearTimeout(searchTimer);
      var val = ev.target.value;
      searchTimer = setTimeout(function () {
        state.search = val.trim();
        state.page = 1;
        loadList();
      }, 300);
    });

    /* ================================================================
       Create / Edit Requirement modal
       ================================================================ */
    var formModal = $("rrq-form-modal");

    function openFormModal(form) {
      $("rrq-form-error").style.display = "none";
      $("rrq-form-requirement-for").textContent = pageData.company_name || "Company";

      if (form) {
        $("rrq-form-id").value = form.id || "";
        $("rrq-form-client-name").value = form.client_name || "";
        $("rrq-form-contact-person").value = form.client_contact_person || "";
        $("rrq-form-coordinator").value = form.coordinator || "";
        $("rrq-form-requestor").value = form.requestor || "";
        $("rrq-form-assigned-to").value = form.assigned_to || "";
        $("rrq-form-skill").value = form.skill || "";
        $("rrq-form-job-title").value = form.job_title || "";
        $("rrq-form-priority").value = form.priority || "3";
        $("rrq-form-status").value = form.status || "not_started";
        $("rrq-form-description").value = form.job_description || "";
        $("rrq-form-title").textContent = "Edit Requirement";
        $("rrq-form-sub").textContent = "Update the job requirement details";
        $("rrq-form-submit-label").textContent = "Save Changes";
      } else {
        $("rrq-form-id").value = "";
        ["rrq-form-client-name", "rrq-form-contact-person", "rrq-form-coordinator",
         "rrq-form-requestor", "rrq-form-assigned-to", "rrq-form-skill",
         "rrq-form-job-title", "rrq-form-description"].forEach(function (id) { $(id).value = ""; });
        $("rrq-form-priority").value = "3";
        $("rrq-form-status").value = "not_started";
        $("rrq-form-title").textContent = "Create New Requirement";
        $("rrq-form-sub").textContent = "Fill in the job requirement details";
        $("rrq-form-submit-label").textContent = "Create Requirement";
      }
      formModal.classList.add("is-open");
    }

    function closeFormModal() { formModal.classList.remove("is-open"); }

    $("rrq-add-btn").addEventListener("click", function () { openFormModal(null); });
    root.querySelectorAll('[data-action="close-form-modal"]').forEach(function (el) {
      el.addEventListener("click", closeFormModal);
    });
    formModal.addEventListener("click", function (ev) { if (ev.target === formModal) closeFormModal(); });

    $("rrq-form-submit").addEventListener("click", function () {
      var payload = {
        id: $("rrq-form-id").value || null,
        client_name: $("rrq-form-client-name").value.trim(),
        client_contact_person: $("rrq-form-contact-person").value.trim(),
        coordinator: $("rrq-form-coordinator").value.trim(),
        requestor: $("rrq-form-requestor").value.trim(),
        assigned_to: $("rrq-form-assigned-to").value.trim(),
        skill: $("rrq-form-skill").value.trim(),
        job_title: $("rrq-form-job-title").value.trim(),
        priority: $("rrq-form-priority").value,
        status: $("rrq-form-status").value,
        job_description: $("rrq-form-description").value.trim(),
      };

      var required = ["client_name", "client_contact_person", "coordinator", "requestor", "skill", "job_title", "job_description"];
      var missing = required.some(function (k) { return !payload[k]; });
      var errEl = $("rrq-form-error");
      if (missing) {
        errEl.textContent = "Please fill in all required fields.";
        errEl.style.display = "";
        return;
      }

      postJSON("/hrsd/recruitment/requirements/save", payload).then(function (data) {
        if (!data.ok) {
          errEl.textContent = data.error || "Something went wrong.";
          errEl.style.display = "";
          return;
        }
        addKnownName(CLIENT_NAMES, data.new_client);
        (data.new_employees || []).forEach(function (n) { addKnownName(EMPLOYEE_NAMES, n); });
        closeFormModal();
        loadList();
        if (state.detailId && state.detailId === data.requirement.id) {
          openDetailModal(state.detailId);
        }
      });
    });

    /* ================================================================
       Requirement detail modal
       ================================================================ */
    var detailModal = $("rrq-detail-modal");
    var currentDetail = null;

    function formatDescription(text) {
      var lines = (text || "").split("\n");
      var html = "";
      lines.forEach(function (line) {
        var trimmed = line.trim();
        if (!trimmed) return;
        if (/^\s+-/.test(line)) {
          html += '<p class="rrq-desc-subbullet">' + escapeHtml(trimmed.replace(/^-\s*/, "")) + '</p>';
        } else if (trimmed.charAt(0) === "-") {
          html += '<p class="rrq-desc-bullet">' + escapeHtml(trimmed.replace(/^-\s*/, "")) + '</p>';
        } else if (trimmed.charAt(trimmed.length - 1) === ":") {
          html += '<p class="rrq-desc-heading">' + escapeHtml(trimmed) + '</p>';
        } else {
          html += '<p>' + escapeHtml(trimmed) + '</p>';
        }
      });
      return html || '<p>&#8212;</p>';
    }

    function buildDetailsPanel(r) {
      var f = r.form;
      var pairs = [
        ["Number", r.code, null],
        ["Requirement For", f.requirement_for, null],
        ["Client Name", f.client_name, null],
        ["Client Contact", f.client_contact_person, null],
        ["Coordinator", f.coordinator, null],
        ["Assigned To", f.assigned_to || "—", null],
        ["Requestor", f.requestor, null],
        ["Priority", r.priority_label, "priority"],
        ["Status", r.status_label, "status"],
        ["Skill", f.skill, null],
        ["Job Title", f.job_title, null],
        ["Open Date", r.open_date, null],
      ];
      var html = '<div class="rrq-detail-grid">';
      pairs.forEach(function (p) {
        var value;
        if (p[2] === "priority") {
          value = '<span class="rrq-req-priority is-' + r.priority_color + '">' + escapeHtml(p[1]) + '</span>';
        } else if (p[2] === "status") {
          value = '<span class="rrq-status-badge is-' + (STATUS_COLORS[r.status] || 'blue') + '">' + escapeHtml(p[1]) + '</span>';
        } else {
          value = escapeHtml(p[1]);
        }
        html += '<div class="rrq-detail-item"><label>' + p[0] + '</label><div class="rrq-detail-value">' + value + '</div></div>';
      });
      html += '</div>';
      html += '<div class="rrq-detail-item is-full" style="margin-top:18px;"><label>Job Description</label>' +
        '<div class="rrq-detail-desc-box">' + formatDescription(f.job_description) + '</div></div>';
      return html;
    }

    function buildCandidateRow(c) {
      var meta = [];
      if (c.experience_years) meta.push('<span class="rrq-candidate-meta-item">' + svg("trendingUp") + '<span>' + c.experience_years + ' yrs exp</span></span>');
      if (c.current_salary) meta.push('<span class="rrq-candidate-meta-item">' + svg("dollar") + '<span>' + c.current_salary + 'LPA</span></span>');
      if (c.mobile) meta.push('<span class="rrq-candidate-meta-item">' + svg("phone") + '<span>' + escapeHtml(c.mobile) + '</span></span>');
      if (c.resume_url) meta.push('<a class="rrq-candidate-meta-item is-link" href="' + c.resume_url + '" target="_blank">' + svg("paperclip") + '<span>' + escapeHtml(c.resume_filename) + '</span></a>');

      return '<div class="rrq-candidate-row" data-id="' + c.id + '">' +
        '<div class="rrq-candidate-avatar is-' + c.avatar_color + '">' + escapeHtml(c.avatar_initials) + '</div>' +
        '<div class="rrq-candidate-main">' +
          '<div class="rrq-candidate-name">' + escapeHtml(c.name) + '</div>' +
          '<div class="rrq-candidate-code">' + escapeHtml(c.code) + '</div>' +
        '</div>' +
        '<div class="rrq-candidate-meta">' + meta.join("") + '</div>' +
        '<span class="rrq-status-badge is-blue">' + escapeHtml(c.interview_status_label) + '</span>' +
        '<div class="rrq-candidate-actions">' +
          '<button type="button" class="rrq-icon-btn-sm" data-action="edit-candidate" data-id="' + c.id + '">' + svg("edit") + '</button>' +
          '<button type="button" class="rrq-icon-btn-sm" data-action="view-candidate" data-id="' + c.id + '">' + svg("chevronRight") + '</button>' +
        '</div>' +
      '</div>';
    }

    /* ================================================================
       Candidate detail view
       ================================================================ */
    var candidateDetailModal = $("rrq-candidate-detail-modal");
    var candidateDetailCurrent = null;

    function buildCandidateDetailBody(c) {
      var req = currentDetail ? currentDetail.requirement : null;
      var fields = [
        ["Number", c.code],
        ["Candidate Name", c.name],
        ["Current Salary", c.current_salary ? c.current_salary + " LPA" : "—"],
        ["Expected Salary", c.expected_salary ? c.expected_salary + " LPA" : "—"],
        ["Email ID", c.email || "—"],
        ["Mobile Number", c.mobile || "—"],
        ["Current Location", c.current_location || "—"],
        ["Experience (Years)", c.experience_years || "—"],
        ["Skill", req ? req.skill : "—"],
        ["Coordinator", c.coordinator || "—"],
        ["Client Name", req ? req.client_name : "—"],
        ["Notice Period", c.notice_period || "—"],
        ["Closing Rate", c.closing_rate ? c.closing_rate + " LPA" : "—"],
        ["Deployed", c.deployed ? "Yes" : "No"],
      ];

      var html = "";
      if (c.resume_url) {
        html += '<div class="rrq-resume-banner">' + svg("fileCheck") +
          '<span class="rrq-resume-banner-name">' + escapeHtml(c.resume_filename) + '</span>' +
          '<a href="' + c.resume_url + '" target="_blank" class="rrq-resume-banner-link">' + svg("download") + 'View</a>' +
        '</div>';
      }

      html += '<div class="rrq-detail-grid">';
      fields.forEach(function (f) {
        html += '<div class="rrq-detail-item"><label>' + escapeHtml(f[0]) + '</label><div class="rrq-detail-value">' + escapeHtml(f[1]) + '</div></div>';
      });
      html += '</div>';

      var steps = pageData.interview_status_options;
      var currentIdx = -1;
      steps.forEach(function (s, i) { if (s[0] === c.interview_status) currentIdx = i; });

      html += '<div class="rrq-section-label" style="margin-top:22px;">Interview Status</div>';
      html += '<div class="rrq-stepper">';
      steps.forEach(function (s, i) {
        var stepClass = i < currentIdx ? "is-done" : (i === currentIdx ? "is-current" : "");
        html += '<div class="rrq-step ' + stepClass + '">' +
          '<div class="rrq-step-dot">' + (i < currentIdx ? svg("check") : '') + '</div>' +
          '<div class="rrq-step-label">' + escapeHtml(s[1]) + '</div>' +
        '</div>';
      });
      html += '</div>';

      html += '<div class="rrq-field" style="margin-top:20px;"><label>Update State</label>' +
        '<select id="rrq-cand-detail-status">' +
        steps.map(function (s) {
          return '<option value="' + s[0] + '"' + (s[0] === c.interview_status ? ' selected="selected"' : '') + '>' + escapeHtml(s[1]) + '</option>';
        }).join("") +
        '</select></div>';

      return html;
    }

    function renderCandidateDetailBody(c) {
      candidateDetailCurrent = c;
      $("rrq-cand-detail-title").textContent = c.name;
      $("rrq-cand-detail-sub").textContent = c.code;
      $("rrq-cand-detail-body").innerHTML = buildCandidateDetailBody(c);
      $("rrq-cand-detail-status").addEventListener("change", function (ev) {
        updateCandidateStatus(candidateDetailCurrent, ev.target.value);
      });
    }

    function openCandidateDetailModal(c) {
      renderCandidateDetailBody(c);
      candidateDetailModal.classList.add("is-open");
    }

    function closeCandidateDetailModal() { candidateDetailModal.classList.remove("is-open"); }

    function updateCandidateStatus(c, newStatus) {
      var payload = {
        id: c.id, requirement_id: state.detailId, name: c.name,
        current_salary: c.current_salary, expected_salary: c.expected_salary,
        email: c.email, mobile: c.mobile, current_location: c.current_location,
        experience_years: c.experience_years, notice_period: c.notice_period || null,
        interview_status: newStatus, coordinator: c.coordinator,
        closing_rate: c.closing_rate, deployed: c.deployed,
      };
      postJSON("/hrsd/recruitment/requirements/candidate/save", payload).then(function (data) {
        if (!data.ok) return;
        var updated = data.candidate;
        if (currentDetail) {
          currentDetail.candidates = currentDetail.candidates.map(function (x) { return x.id === updated.id ? updated : x; });
          renderCandidates(currentDetail.candidates);
        }
        renderCandidateDetailBody(updated);
      });
    }

    root.querySelectorAll('[data-action="close-candidate-detail-modal"]').forEach(function (el) {
      el.addEventListener("click", closeCandidateDetailModal);
    });
    candidateDetailModal.addEventListener("click", function (ev) { if (ev.target === candidateDetailModal) closeCandidateDetailModal(); });
    $("rrq-cand-detail-back").addEventListener("click", closeCandidateDetailModal);
    $("rrq-cand-detail-edit-btn").addEventListener("click", function () {
      if (!candidateDetailCurrent) return;
      closeCandidateDetailModal();
      openCandidateModal(state.detailId, candidateDetailCurrent);
    });

    function renderCandidates(candidates) {
      $("rrq-tab-candidate-count").textContent = candidates.length;
      var list = $("rrq-candidates-list");
      if (!candidates.length) {
        list.innerHTML = '<div class="rrq-notes-empty">No candidates added yet.</div>';
      } else {
        list.innerHTML = candidates.map(buildCandidateRow).join("");
        list.querySelectorAll('[data-action="edit-candidate"]').forEach(function (btn) {
          btn.addEventListener("click", function () {
            var cid = parseInt(btn.getAttribute("data-id"), 10);
            var cand = currentDetail.candidates.filter(function (c) { return c.id === cid; })[0];
            openCandidateModal(state.detailId, cand);
          });
        });
        list.querySelectorAll('[data-action="view-candidate"]').forEach(function (btn) {
          btn.addEventListener("click", function () {
            var cid = parseInt(btn.getAttribute("data-id"), 10);
            var cand = currentDetail.candidates.filter(function (c) { return c.id === cid; })[0];
            if (cand) openCandidateDetailModal(cand);
          });
        });
      }
    }

    function renderNotes(notes) {
      $("rrq-tab-note-count").textContent = notes.length;
      var list = $("rrq-notes-list");
      if (!notes.length) {
        list.innerHTML = '<div class="rrq-notes-empty">No work notes yet.</div>';
      } else {
        list.innerHTML = notes.map(function (n) {
          return '<div class="rrq-note-item">' +
            '<span class="rrq-note-author">' + escapeHtml(n.author) + '</span>' +
            '<span class="rrq-note-date">' + escapeHtml(n.create_date) + '</span>' +
            '<div class="rrq-note-body">' + escapeHtml(n.body) + '</div>' +
          '</div>';
        }).join("");
      }
    }

    function setDetailTab(tab) {
      state.detailTab = tab;
      root.querySelectorAll(".rrq-modal-tab").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-tab") === tab);
      });
      root.querySelectorAll(".rrq-tab-panel").forEach(function (panel) {
        panel.classList.toggle("is-active", panel.id === "rrq-tab-panel-" + tab);
      });
    }

    root.querySelectorAll("#rrq-detail-modal .rrq-modal-tab").forEach(function (btn) {
      btn.addEventListener("click", function () { setDetailTab(btn.getAttribute("data-tab")); });
    });

    function openDetailModal(id) {
      getJSON("/hrsd/recruitment/requirements/detail?id=" + id).then(function (data) {
        if (!data.ok) return;
        currentDetail = data;
        state.detailId = id;

        var r = data.requirement;
        $("rrq-detail-title").textContent = r.job_title;
        $("rrq-detail-sub").textContent = r.code + " · " + r.form.client_name + " · " + r.priority_label;
        $("rrq-tab-panel-details").innerHTML = buildDetailsPanel(r);
        renderCandidates(data.candidates);
        renderNotes(data.notes);
        $("rrq-note-input").value = "";

        setDetailTab("details");
        detailModal.classList.add("is-open");
      });
    }

    function closeDetailModal() { detailModal.classList.remove("is-open"); }

    root.querySelectorAll('[data-action="close-detail-modal"]').forEach(function (el) {
      el.addEventListener("click", closeDetailModal);
    });
    detailModal.addEventListener("click", function (ev) { if (ev.target === detailModal) closeDetailModal(); });

    $("rrq-detail-edit-btn").addEventListener("click", function () {
      if (!currentDetail) return;
      closeDetailModal();
      openFormModal(currentDetail.requirement.form);
    });

    $("rrq-add-candidate-btn").addEventListener("click", function () {
      openCandidateModal(state.detailId, null);
    });

    $("rrq-note-submit").addEventListener("click", function () {
      var text = $("rrq-note-input").value.trim();
      if (!text || !state.detailId) return;
      postJSON("/hrsd/recruitment/requirements/note/add", {
        requirement_id: state.detailId, body: text,
      }).then(function (data) {
        if (!data.ok) return;
        currentDetail.notes.unshift(data.note);
        renderNotes(currentDetail.notes);
        $("rrq-note-input").value = "";
      });
    });

    /* ================================================================
       Add / Edit Candidate modal
       ================================================================ */
    var candidateModal = $("rrq-candidate-modal");
    var resumeBase64 = null;
    var resumeFilename = null;

    function resetUploadBox() {
      resumeBase64 = null;
      resumeFilename = null;
      var box = $("rrq-resume-upload");
      box.classList.remove("has-file");
      $("rrq-resume-upload-title").textContent = "Click to upload resume";
      $("rrq-resume-input").value = "";
    }

    $("rrq-resume-input").addEventListener("change", function (ev) {
      var file = ev.target.files[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        alert("File exceeds 5 MB limit.");
        resetUploadBox();
        return;
      }
      var reader = new FileReader();
      reader.onload = function () {
        var result = reader.result || "";
        resumeBase64 = result.split(",")[1] || "";
        resumeFilename = file.name;
        $("rrq-resume-upload").classList.add("has-file");
        $("rrq-resume-upload-title").textContent = file.name;
      };
      reader.readAsDataURL(file);
    });

    function openCandidateModal(requirementId, candidate) {
      $("rrq-candidate-form-error").style.display = "none";
      $("rrq-candidate-requirement-id").value = requirementId;
      resetUploadBox();

      if (candidate) {
        $("rrq-candidate-id").value = candidate.id;
        $("rrq-candidate-name").value = candidate.name || "";
        $("rrq-candidate-current-salary").value = candidate.current_salary || "";
        $("rrq-candidate-expected-salary").value = candidate.expected_salary || "";
        $("rrq-candidate-email").value = candidate.email || "";
        $("rrq-candidate-mobile").value = candidate.mobile || "";
        $("rrq-candidate-location").value = candidate.current_location || "";
        $("rrq-candidate-experience").value = candidate.experience_years || "";
        $("rrq-candidate-notice").value = candidate.notice_period || "";
        $("rrq-candidate-status").value = candidate.interview_status || "to_interview";
        $("rrq-candidate-coordinator").value = candidate.coordinator || "";
        $("rrq-candidate-closing-rate").value = candidate.closing_rate || "";
        $("rrq-candidate-deployed").checked = !!candidate.deployed;
        if (candidate.resume_filename) {
          $("rrq-resume-upload").classList.add("has-file");
          $("rrq-resume-upload-title").textContent = candidate.resume_filename;
        }
        $("rrq-candidate-title").textContent = "Edit Candidate";
        $("rrq-candidate-sub").textContent = candidate.code || "";
        $("rrq-candidate-submit-label").textContent = "Save Changes";
      } else {
        $("rrq-candidate-id").value = "";
        ["rrq-candidate-name", "rrq-candidate-current-salary", "rrq-candidate-expected-salary",
         "rrq-candidate-email", "rrq-candidate-mobile", "rrq-candidate-location",
         "rrq-candidate-experience", "rrq-candidate-notice", "rrq-candidate-coordinator",
         "rrq-candidate-closing-rate"].forEach(function (id) { $(id).value = ""; });
        $("rrq-candidate-status").value = "to_interview";
        $("rrq-candidate-deployed").checked = false;
        $("rrq-candidate-title").textContent = "Add Candidate";
        var req = currentDetail ? currentDetail.requirement : null;
        $("rrq-candidate-sub").textContent = req ? (req.job_title + " · " + req.code) : "";
        $("rrq-candidate-submit-label").textContent = "Add Candidate";
      }
      candidateModal.classList.add("is-open");
    }

    function closeCandidateModal() { candidateModal.classList.remove("is-open"); }

    root.querySelectorAll('[data-action="close-candidate-modal"]').forEach(function (el) {
      el.addEventListener("click", closeCandidateModal);
    });
    candidateModal.addEventListener("click", function (ev) { if (ev.target === candidateModal) closeCandidateModal(); });

    $("rrq-candidate-submit").addEventListener("click", function () {
      var name = $("rrq-candidate-name").value.trim();
      var errEl = $("rrq-candidate-form-error");
      if (!name) {
        errEl.textContent = "Candidate name is required.";
        errEl.style.display = "";
        return;
      }

      var payload = {
        id: $("rrq-candidate-id").value || null,
        requirement_id: $("rrq-candidate-requirement-id").value,
        name: name,
        current_salary: $("rrq-candidate-current-salary").value,
        expected_salary: $("rrq-candidate-expected-salary").value,
        email: $("rrq-candidate-email").value.trim(),
        mobile: $("rrq-candidate-mobile").value.trim(),
        current_location: $("rrq-candidate-location").value.trim(),
        experience_years: $("rrq-candidate-experience").value,
        notice_period: $("rrq-candidate-notice").value || null,
        interview_status: $("rrq-candidate-status").value,
        coordinator: $("rrq-candidate-coordinator").value.trim(),
        closing_rate: $("rrq-candidate-closing-rate").value,
        deployed: $("rrq-candidate-deployed").checked,
      };
      if (resumeBase64) {
        payload.resume_data = resumeBase64;
        payload.resume_filename = resumeFilename;
      }

      postJSON("/hrsd/recruitment/requirements/candidate/save", payload).then(function (data) {
        if (!data.ok) {
          errEl.textContent = data.error || "Something went wrong.";
          errEl.style.display = "";
          return;
        }
        (data.new_employees || []).forEach(function (n) { addKnownName(EMPLOYEE_NAMES, n); });
        closeCandidateModal();
        loadList();
        if (state.detailId) openDetailModal(state.detailId);
      });
    });

    /* ================================================================
       Bulk upload — auto-fill requirements or candidates from documents
       ================================================================ */
    function getCsrf() {
      var metas = document.getElementsByTagName("meta");
      for (var i = 0; i < metas.length; i++) {
        if (metas[i].getAttribute("name") === "csrf-token") return metas[i].getAttribute("content");
      }
      var match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
      return match ? decodeURIComponent(match[1]) : "";
    }

    var uploadModal = $("rrq-upload-modal");
    var uploadInput = $("rrq-upload-input");
    var uploadMode = "requirement";
    var uploadFiles = [];

    function renderUploadFileList() {
      var el = $("rrq-upload-file-list");
      if (!uploadFiles.length) { el.innerHTML = ""; return; }
      el.innerHTML = uploadFiles.map(function (f, i) {
        return '<div class="rrq-upload-file-row"><span>' + escapeHtml(f.name) + '</span>' +
          '<button type="button" class="rrq-icon-btn-sm" data-remove-index="' + i + '">' + svg("trash") + '</button></div>';
      }).join("");
      el.querySelectorAll("[data-remove-index]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          uploadFiles.splice(parseInt(btn.getAttribute("data-remove-index"), 10), 1);
          renderUploadFileList();
        });
      });
    }

    uploadInput.addEventListener("change", function () {
      uploadFiles = Array.prototype.slice.call(uploadInput.files);
      renderUploadFileList();
    });

    function openUploadModal(mode) {
      uploadMode = mode;
      uploadFiles = [];
      uploadInput.value = "";
      $("rrq-upload-file-list").innerHTML = "";
      $("rrq-upload-results").innerHTML = "";
      $("rrq-upload-error").style.display = "none";
      if (mode === "requirement") {
        $("rrq-upload-title").textContent = "Upload Job Requirement Documents";
        $("rrq-upload-sub").textContent = "We'll auto-extract job title, skills, client and description for each file";
      } else {
        $("rrq-upload-title").textContent = "Upload Resumes";
        $("rrq-upload-sub").textContent = "We'll auto-extract candidate name, email, phone and experience for each file";
      }
      uploadModal.classList.add("is-open");
    }

    function closeUploadModal() { uploadModal.classList.remove("is-open"); }

    $("rrq-upload-requirement-btn").addEventListener("click", function () { openUploadModal("requirement"); });
    $("rrq-upload-candidate-btn").addEventListener("click", function () {
      if (!state.detailId) return;
      openUploadModal("candidate");
    });

    root.querySelectorAll('[data-action="close-upload-modal"]').forEach(function (el) {
      el.addEventListener("click", closeUploadModal);
    });
    uploadModal.addEventListener("click", function (ev) { if (ev.target === uploadModal) closeUploadModal(); });

    function refreshCandidatesTab() {
      getJSON("/hrsd/recruitment/requirements/detail?id=" + state.detailId).then(function (data) {
        if (!data.ok) return;
        currentDetail = data;
        renderCandidates(data.candidates);
      });
    }

    function renderUploadResults(results) {
      var el = $("rrq-upload-results");
      el.innerHTML = results.map(function (r) {
        if (r.ok) {
          var label = uploadMode === "requirement"
            ? (r.requirement && r.requirement.job_title)
            : (r.candidate && r.candidate.name);
          return '<div class="rrq-upload-result is-ok">' + svg("check") +
            '<span>' + escapeHtml(r.filename) + ' → ' + escapeHtml(label || "created") + '</span></div>';
        }
        return '<div class="rrq-upload-result is-fail">' + svg("trash") +
          '<span>' + escapeHtml(r.filename) + ' — ' + escapeHtml(r.error || "failed") + '</span></div>';
      }).join("");
    }

    $("rrq-upload-submit").addEventListener("click", function () {
      var errEl = $("rrq-upload-error");
      errEl.style.display = "none";
      if (!uploadFiles.length) {
        errEl.textContent = "Choose at least one file.";
        errEl.style.display = "";
        return;
      }

      var fd = new FormData();
      fd.append("csrf_token", getCsrf());
      uploadFiles.forEach(function (f) { fd.append("files", f); });

      var url = "/hrsd/recruitment/requirements/upload";
      if (uploadMode === "candidate") {
        url = "/hrsd/recruitment/requirements/candidate/upload";
        fd.append("requirement_id", state.detailId);
      }

      var submitBtn = $("rrq-upload-submit");
      submitBtn.disabled = true;
      $("rrq-upload-submit-label").textContent = "Uploading…";

      fetch(url, { method: "POST", body: fd })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          submitBtn.disabled = false;
          $("rrq-upload-submit-label").textContent = "Upload & Auto-Fill";
          if (!data.ok) {
            errEl.textContent = data.error || "Something went wrong.";
            errEl.style.display = "";
            return;
          }
          renderUploadResults(data.results);
          uploadFiles = [];
          uploadInput.value = "";
          $("rrq-upload-file-list").innerHTML = "";
          if (uploadMode === "requirement") {
            loadList();
          } else if (state.detailId) {
            refreshCandidatesTab();
          }
        })
        .catch(function () {
          submitBtn.disabled = false;
          $("rrq-upload-submit-label").textContent = "Upload & Auto-Fill";
          errEl.textContent = "Upload failed. Please try again.";
          errEl.style.display = "";
        });
    });

    /* ================================================================
       Escape closes topmost modal
       ================================================================ */
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") return;
      if (uploadModal.classList.contains("is-open")) { closeUploadModal(); return; }
      if (candidateModal.classList.contains("is-open")) { closeCandidateModal(); return; }
      if (candidateDetailModal.classList.contains("is-open")) { closeCandidateDetailModal(); return; }
      if (detailModal.classList.contains("is-open")) { closeDetailModal(); return; }
      if (formModal.classList.contains("is-open")) { closeFormModal(); return; }
    });

    /* ================================================================
       Initial paint
       ================================================================ */
    renderStats(pageData.stats);
    renderTabs();
    renderList({
      requirements: pageData.requirements,
      total: pageData.total,
      page: pageData.page,
      page_size: pageData.page_size,
    });
  });
})();
