/* =========================================================================
   AvanteNow HR Portal — Kanban Workspace Board interactions
   ========================================================================= */
(function () {
  "use strict";

  function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  var STAGE_COLUMNS = [
    { key: "to_do", label: "To Do", color: "red" },
    { key: "in_progress", label: "In Progress", color: "orange" },
    { key: "in_review", label: "In Review", color: "purple" },
    { key: "stuck", label: "Stuck", color: "pink" },
    { key: "completed", label: "Completed", color: "green" },
  ];

  var PRIORITY_COLUMNS = [
    { key: "critical", label: "Critical", color: "red" },
    { key: "high", label: "High", color: "orange" },
    { key: "medium", label: "Medium", color: "blue" },
    { key: "low", label: "Low", color: "gray" },
  ];

  var GROUP_DEFS = {
    stage: { columns: STAGE_COLUMNS, getKey: function (t) { return t.stage; } },
    priority: { columns: PRIORITY_COLUMNS, getKey: function (t) { return t.priority; } },
  };

  function $(id) { return document.getElementById(id); }

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) { return r.json(); });
  }

  /* ================================================================
     Dark / light theme toggle
     ================================================================ */
  function initThemeToggle() {
    var btn = $("tsk-theme-toggle");
    if (!btn) return;
    var root = document.documentElement;

    function applyTheme(theme) {
      root.setAttribute("data-theme", theme);
      try { localStorage.setItem("tsk-theme", theme); } catch (e) { /* storage unavailable */ }
      btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    }

    btn.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
      applyTheme(current === "dark" ? "light" : "dark");
    });

    applyTheme(root.getAttribute("data-theme") === "light" ? "light" : "dark");
  }

  onReady(function () {
    initThemeToggle();

    var root = document.querySelector(".tsk-shell");
    if (!root) return;

    var pageData = JSON.parse($("tsk-page-data").textContent || "{}");

    if (pageData.no_employee) {
      $("tsk-empty-state").style.display = "";
      $("tsk-app").style.display = "none";
      return;
    }

    if (pageData.timesheet_url) {
      var link = $("tsk-timesheet-link");
      link.href = pageData.timesheet_url;
      link.style.display = "";
    }

    var state = {
      selectedEmployeeId: pageData.selected_employee_id,
      tasks: pageData.tasks || [],
      groupBy: "stage",
      view: "kanban",
      filters: { priorities: {}, search: "" },
    };

    var employeeById = {};
    pageData.visible_employees.forEach(function (e) { employeeById[e.id] = e; });

    /* ================================================================
       Reporting hierarchy (pure-CSS org-chart tree)
       ================================================================ */
    function buildTreeNode(node) {
      var classes = "tsk-node" + (node.is_me ? " is-me" : "") + (!node.is_visible && !node.is_me ? " is-dim" : "");
      var html = '<li><div class="' + classes + '">' +
        '<div class="tsk-node-avatar is-' + node.color + '">' + escapeHtml(node.initials) + '</div>' +
        '<div class="tsk-node-name">' + escapeHtml(node.name) + (node.is_me ? ' (You)' : '') + '</div>' +
        '</div>';
      if (node.children && node.children.length) {
        html += '<ul>' + node.children.map(buildTreeNode).join("") + '</ul>';
      }
      html += '</li>';
      return html;
    }

    function renderHierarchy() {
      $("tsk-org-tree").innerHTML = '<ul class="tsk-tree">' + buildTreeNode(pageData.hierarchy) + '</ul>';
    }

    /* ================================================================
       Employee switcher
       ================================================================ */
    function renderSwitcher() {
      var el = $("tsk-switcher");
      if (pageData.visible_employees.length <= 1) {
        el.style.display = "none";
        return;
      }
      el.innerHTML = pageData.visible_employees.map(function (e) {
        var active = e.id === state.selectedEmployeeId ? " is-active" : "";
        var label = e.id === pageData.me.id ? "Me" : e.name;
        return '<button type="button" class="tsk-switcher-pill' + active + '" data-id="' + e.id + '">' +
          '<span class="tsk-pill-avatar is-' + e.color + '">' + escapeHtml(e.initials) + '</span>' +
          escapeHtml(label) + '</button>';
      }).join("");
      el.querySelectorAll(".tsk-switcher-pill").forEach(function (btn) {
        btn.addEventListener("click", function () {
          state.selectedEmployeeId = parseInt(btn.getAttribute("data-id"), 10);
          renderSwitcher();
          updateBoardTitle();
          loadTasks();
        });
      });
    }

    function updateBoardTitle() {
      var e = employeeById[state.selectedEmployeeId];
      var isMe = state.selectedEmployeeId === pageData.me.id;
      $("tsk-board-title").textContent = isMe ? "My To-Do (Kanban)" : (e ? e.name : "") + "'s To-Do (Kanban)";
      $("tsk-board-sub").textContent = isMe
        ? "Manage your tasks and track progress"
        : "Viewing tasks as their manager";
    }

    /* ================================================================
       Stats row
       ================================================================ */
    var STAT_ICONS = {
      total: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2h6a1 1 0 0 1 1 1v2H8V3a1 1 0 0 1 1-1Z"/><rect x="5" y="4" width="14" height="18" rx="2"/><path d="M9 12h6M9 16h6"/></svg>',
      to_do: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/></svg>',
      in_progress: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 22h14M5 2h14M6 2v5.5a6 6 0 0 0 2.4 4.8L12 15l3.6-2.7A6 6 0 0 0 18 7.5V2M6 22v-5.5a6 6 0 0 1 2.4-4.8L12 9l3.6 2.7a6 6 0 0 1 2.4 4.8V22"/></svg>',
      completed: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/></svg>',
      progress: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    };

    function renderStats() {
      var el = $("tsk-stats");
      if (!el) return;
      var total = state.tasks.length;
      var todo = state.tasks.filter(function (t) { return t.stage === "to_do"; }).length;
      var inProgress = state.tasks.filter(function (t) { return t.stage === "in_progress"; }).length;
      var done = state.tasks.filter(function (t) { return t.stage === "completed"; }).length;
      var pct = total ? Math.round((done / total) * 100) : 0;

      var cards = [
        { icon: STAT_ICONS.total, color: "blue", value: total, label: "Total Tasks", sub: "All tasks in board" },
        { icon: STAT_ICONS.to_do, color: "pink", value: todo, label: "To Do", sub: "Tasks to start" },
        { icon: STAT_ICONS.in_progress, color: "orange", value: inProgress, label: "In Progress", sub: "Tasks in progress" },
        { icon: STAT_ICONS.completed, color: "green", value: done, label: "Completed", sub: "Tasks done" },
      ];

      el.innerHTML = cards.map(function (c) {
        return '<div class="tsk-stat-card is-' + c.color + '">' +
          '<div class="tsk-stat-icon is-' + c.color + '">' + c.icon + '</div>' +
          '<div><div class="tsk-stat-value">' + c.value + '</div>' +
          '<div class="tsk-stat-label">' + c.label + '</div>' +
          '<div class="tsk-stat-sub">' + c.sub + '</div></div>' +
        '</div>';
      }).join("") +
        '<div class="tsk-stat-card is-blue">' +
          '<div class="tsk-stat-icon is-blue">' + STAT_ICONS.progress + '</div>' +
          '<div style="flex:1">' +
            '<div class="tsk-stat-value">' + pct + '%</div>' +
            '<div class="tsk-stat-label">Progress</div>' +
            '<div class="tsk-stat-progress"><div class="tsk-stat-progress-bar" style="width:' + pct + '%"></div></div>' +
          '</div>' +
        '</div>';
    }

    /* ================================================================
       Filtering
       ================================================================ */
    function getFilteredTasks() {
      var activePriorities = Object.keys(state.filters.priorities).filter(function (k) { return state.filters.priorities[k]; });
      var search = state.filters.search.trim().toLowerCase();
      return state.tasks.filter(function (t) {
        if (activePriorities.length && activePriorities.indexOf(t.priority) === -1) return false;
        if (search) {
          var haystack = (t.name + " " + (t.tag || "") + " " + (t.description || "")).toLowerCase();
          if (haystack.indexOf(search) === -1) return false;
        }
        return true;
      });
    }

    function updateFilterCount() {
      var activePriorities = Object.keys(state.filters.priorities).filter(function (k) { return state.filters.priorities[k]; });
      var count = activePriorities.length + (state.filters.search.trim() ? 1 : 0);
      var badge = $("tsk-filter-count");
      var btn = $("tsk-filter-btn");
      badge.textContent = count;
      badge.style.display = count ? "" : "none";
      btn.classList.toggle("is-active", count > 0);
    }

    function initFilterPanel() {
      var btn = $("tsk-filter-btn");
      var panel = $("tsk-filter-panel");
      var searchInput = $("tsk-filter-search");

      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        panel.classList.toggle("is-open");
      });
      panel.addEventListener("click", function (ev) { ev.stopPropagation(); });
      document.addEventListener("click", function () { panel.classList.remove("is-open"); });

      panel.querySelectorAll("[data-filter-priority]").forEach(function (cb) {
        cb.addEventListener("change", function () {
          state.filters.priorities[cb.getAttribute("data-filter-priority")] = cb.checked;
          updateFilterCount();
          renderCurrentView();
        });
      });

      searchInput.addEventListener("input", function () {
        state.filters.search = searchInput.value;
        updateFilterCount();
        renderCurrentView();
      });

      $("tsk-filter-clear").addEventListener("click", function () {
        state.filters.priorities = {};
        state.filters.search = "";
        searchInput.value = "";
        panel.querySelectorAll("[data-filter-priority]").forEach(function (cb) { cb.checked = false; });
        updateFilterCount();
        renderCurrentView();
      });
    }

    /* ================================================================
       Group-by + view toggle
       ================================================================ */
    function initToolbarControls() {
      $("tsk-groupby-select").addEventListener("change", function (ev) {
        state.groupBy = ev.target.value;
        renderCurrentView();
      });

      $("tsk-view-kanban").addEventListener("click", function () { setView("kanban"); });
      $("tsk-view-list").addEventListener("click", function () { setView("list"); });
    }

    function setView(view) {
      state.view = view;
      $("tsk-view-kanban").classList.toggle("is-active", view === "kanban");
      $("tsk-view-list").classList.toggle("is-active", view === "list");
      $("tsk-board").style.display = view === "kanban" ? "" : "none";
      $("tsk-list").style.display = view === "list" ? "" : "none";
      renderCurrentView();
    }

    /* ================================================================
       Kanban board
       ================================================================ */
    var CARD_DATE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>';
    var MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    function formatDateShort(dateStr) {
      var parts = (dateStr || "").split("-");
      if (parts.length !== 3) return dateStr;
      var month = parseInt(parts[1], 10) - 1;
      return MONTH_SHORT[month] + " " + parseInt(parts[2], 10);
    }

    function buildCard(t, draggable) {
      var pills = "";
      if (t.hours) pills += '<span class="tsk-pill is-chip">' + t.hours + 'h</span>';
      pills += '<span class="tsk-pill is-solid is-' + t.priority_color + '">' + escapeHtml(t.priority_label) + '</span>';
      if (t.tag) pills += '<span class="tsk-pill is-tag">' + escapeHtml(t.tag) + '</span>';

      return '<div class="tsk-card" draggable="' + (draggable ? "true" : "false") + '" data-id="' + t.id + '">' +
        '<div class="tsk-card-title">' + escapeHtml(t.name) + '</div>' +
        (t.description ? '<div class="tsk-card-desc">' + escapeHtml(t.description) + '</div>' : '') +
        '<div class="tsk-card-top">' + pills + '</div>' +
        '<div class="tsk-card-footer">' +
          '<div class="tsk-card-avatar is-' + t.avatar_color + '">' + escapeHtml(t.avatar_initials) + '</div>' +
          (t.date ? '<span class="tsk-card-date">' + CARD_DATE_ICON + formatDateShort(t.date) + '</span>' : '<span></span>') +
        '</div>' +
      '</div>';
    }

    function renderBoard() {
      var group = GROUP_DEFS[state.groupBy] || GROUP_DEFS.stage;
      var draggable = state.groupBy === "stage";
      var filtered = getFilteredTasks();
      var board = $("tsk-board");
      board.innerHTML = group.columns.map(function (col) {
        var tasks = filtered.filter(function (t) { return group.getKey(t) === col.key; });
        var body = tasks.length
          ? tasks.map(function (t) { return buildCard(t, draggable); }).join("")
          : '<div class="tsk-column-empty">No tasks</div>';
        return '<div class="tsk-column">' +
          '<div class="tsk-column-header is-' + col.color + '">' +
            '<span>' + col.label + '</span><span class="tsk-column-count">' + tasks.length + '</span>' +
          '</div>' +
          '<div class="tsk-column-body" data-key="' + col.key + '">' + body + '</div>' +
          (draggable ? '<button type="button" class="tsk-add-task-btn" data-stage="' + col.key + '">' +
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
            ' Add task</button>' : '') +
        '</div>';
      }).join("");

      board.querySelectorAll(".tsk-card").forEach(function (card) {
        card.addEventListener("click", function () {
          var id = parseInt(card.getAttribute("data-id"), 10);
          var task = state.tasks.filter(function (t) { return t.id === id; })[0];
          if (task) openTaskModal(task);
        });
        card.addEventListener("dragstart", function (ev) {
          ev.dataTransfer.setData("text/plain", card.getAttribute("data-id"));
          ev.dataTransfer.effectAllowed = "move";
        });
      });

      board.querySelectorAll(".tsk-add-task-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
          openTaskModal(null, btn.getAttribute("data-stage"));
        });
      });

      if (!draggable) return;
      board.querySelectorAll(".tsk-column-body").forEach(function (zone) {
        zone.addEventListener("dragover", function (ev) {
          ev.preventDefault();
          zone.classList.add("is-drag-over");
        });
        zone.addEventListener("dragleave", function () { zone.classList.remove("is-drag-over"); });
        zone.addEventListener("drop", function (ev) {
          ev.preventDefault();
          zone.classList.remove("is-drag-over");
          var id = parseInt(ev.dataTransfer.getData("text/plain"), 10);
          var stage = zone.getAttribute("data-key");
          moveTask(id, stage);
        });
      });
    }

    /* ================================================================
       List view
       ================================================================ */
    function buildListRow(t) {
      return '<div class="tsk-list-row" data-id="' + t.id + '">' +
        '<div class="tsk-list-col-task tsk-list-task">' +
          '<span class="tsk-list-task-name">' + escapeHtml(t.name) + '</span>' +
          (t.tag ? '<span class="tsk-list-task-tag">' + escapeHtml(t.tag) + '</span>' : '') +
        '</div>' +
        '<div class="tsk-list-col-assignee tsk-list-assignee">' +
          '<div class="tsk-card-avatar is-' + t.avatar_color + '">' + escapeHtml(t.avatar_initials) + '</div>' +
          '<span>' + escapeHtml(t.employee_name) + '</span>' +
        '</div>' +
        '<div class="tsk-list-col-stage"><span class="tsk-pill is-gray">' + escapeHtml(stageLabel(t.stage)) + '</span></div>' +
        '<div class="tsk-list-col-priority"><span class="tsk-pill is-' + t.priority_color + '">' + escapeHtml(t.priority_label) + '</span></div>' +
        '<div class="tsk-list-col-date tsk-list-hours">' + (t.date || "—") + '</div>' +
        '<div class="tsk-list-col-hours tsk-list-hours">' + (t.hours ? t.hours + 'h' : '—') + '</div>' +
      '</div>';
    }

    function stageLabel(key) {
      var col = STAGE_COLUMNS.filter(function (c) { return c.key === key; })[0];
      return col ? col.label : key;
    }

    function renderList() {
      var filtered = getFilteredTasks();
      var el = $("tsk-list");
      var head = '<div class="tsk-list-row tsk-list-row-head">' +
        '<div class="tsk-list-col-task tsk-list-col-label">Task</div>' +
        '<div class="tsk-list-col-assignee tsk-list-col-label">Assignee</div>' +
        '<div class="tsk-list-col-stage tsk-list-col-label">Status</div>' +
        '<div class="tsk-list-col-priority tsk-list-col-label">Priority</div>' +
        '<div class="tsk-list-col-date tsk-list-col-label">Date</div>' +
        '<div class="tsk-list-col-hours tsk-list-col-label">Hours</div>' +
      '</div>';

      el.innerHTML = head + (filtered.length
        ? filtered.map(buildListRow).join("")
        : '<div class="tsk-list-empty">No tasks match your filters</div>');

      el.querySelectorAll(".tsk-list-row[data-id]").forEach(function (row) {
        row.addEventListener("click", function () {
          var id = parseInt(row.getAttribute("data-id"), 10);
          var task = state.tasks.filter(function (t) { return t.id === id; })[0];
          if (task) openTaskModal(task);
        });
      });
    }

    function renderCurrentView() {
      renderStats();
      if (state.view === "list") renderList();
      else renderBoard();
    }

    function loadTasks() {
      postJSON("/hrsd/tasks/list", { employee_id: state.selectedEmployeeId }).then(function (data) {
        if (!data.ok) return;
        state.tasks = data.tasks;
        renderCurrentView();
      });
    }

    function moveTask(id, stage) {
      var task = state.tasks.filter(function (t) { return t.id === id; })[0];
      if (task) task.stage = stage;
      renderCurrentView();
      postJSON("/hrsd/tasks/move", { id: id, stage: stage }).then(function (data) {
        if (!data.ok) { loadTasks(); return; }
        loadTasks();
      });
    }

    /* ================================================================
       Create / edit task modal
       ================================================================ */
    var formModal = $("tsk-form-modal");
    var employeeSelect = $("tsk-form-employee");
    employeeSelect.innerHTML = pageData.visible_employees.map(function (e) {
      return '<option value="' + e.id + '">' + escapeHtml(e.name) + '</option>';
    }).join("");

    function openTaskModal(task, presetStage) {
      $("tsk-form-error").style.display = "none";

      if (task) {
        $("tsk-form-id").value = task.id;
        $("tsk-form-name").value = task.name;
        employeeSelect.value = task.employee_id;
        $("tsk-form-stage").value = task.stage;
        $("tsk-form-priority").value = task.priority;
        $("tsk-form-tag").value = task.tag || "";
        $("tsk-form-date").value = task.date || "";
        $("tsk-form-hours").value = task.hours || "";
        $("tsk-form-description").value = task.description || "";
        $("tsk-form-title").textContent = "Edit Task";
        $("tsk-form-submit-label").textContent = "Save Changes";
        $("tsk-form-delete").style.display = "";
      } else {
        $("tsk-form-id").value = "";
        $("tsk-form-name").value = "";
        employeeSelect.value = state.selectedEmployeeId;
        $("tsk-form-stage").value = presetStage || "to_do";
        $("tsk-form-priority").value = "medium";
        $("tsk-form-tag").value = "";
        $("tsk-form-date").value = new Date().toISOString().slice(0, 10);
        $("tsk-form-hours").value = "";
        $("tsk-form-description").value = "";
        $("tsk-form-title").textContent = "New Task";
        $("tsk-form-submit-label").textContent = "Create Task";
        $("tsk-form-delete").style.display = "none";
      }
      formModal.classList.add("is-open");
    }

    function closeTaskModal() { formModal.classList.remove("is-open"); }

    root.querySelectorAll('[data-action="close-form-modal"]').forEach(function (el) {
      el.addEventListener("click", closeTaskModal);
    });
    formModal.addEventListener("click", function (ev) { if (ev.target === formModal) closeTaskModal(); });

    $("tsk-form-submit").addEventListener("click", function () {
      var name = $("tsk-form-name").value.trim();
      var errEl = $("tsk-form-error");
      if (!name) {
        errEl.textContent = "Task title is required.";
        errEl.style.display = "";
        return;
      }
      var payload = {
        id: $("tsk-form-id").value || null,
        name: name,
        employee_id: employeeSelect.value,
        stage: $("tsk-form-stage").value,
        priority: $("tsk-form-priority").value,
        tag: $("tsk-form-tag").value.trim(),
        date: $("tsk-form-date").value,
        hours: $("tsk-form-hours").value,
        description: $("tsk-form-description").value.trim(),
      };
      postJSON("/hrsd/tasks/save", payload).then(function (data) {
        if (!data.ok) {
          errEl.textContent = data.error || "Something went wrong.";
          errEl.style.display = "";
          return;
        }
        closeTaskModal();
        loadTasks();
      });
    });

    $("tsk-form-delete").addEventListener("click", function () {
      var id = $("tsk-form-id").value;
      if (!id || !window.confirm("Delete this task?")) return;
      postJSON("/hrsd/tasks/delete", { id: id }).then(function (data) {
        if (!data.ok) return;
        closeTaskModal();
        loadTasks();
      });
    });

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && formModal.classList.contains("is-open")) closeTaskModal();
    });

    /* ================================================================
       Initial paint
       ================================================================ */
    initFilterPanel();
    initToolbarControls();
    renderHierarchy();
    renderSwitcher();
    updateBoardTitle();
    renderCurrentView();
  });
})();
