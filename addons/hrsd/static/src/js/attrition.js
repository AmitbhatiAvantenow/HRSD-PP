/* ==========================================================================
   Predictive Attrition — dashboard logic
   ========================================================================== */
(function () {
  "use strict";

  /* ---- helpers ---------------------------------------------------------- */
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

  function tenureLabel(months) {
    if (!months && months !== 0) return '—';
    if (months < 1)  return '< 1 mo';
    if (months < 12) return months + ' mo';
    var y = Math.floor(months / 12);
    var m = months % 12;
    return m ? (y + 'y ' + m + 'm') : (y + ' yr' + (y !== 1 ? 's' : ''));
  }

  function initials(name) {
    return (name || '').split(' ').filter(Boolean).slice(0, 2)
      .map(function (p) { return p[0]; }).join('').toUpperCase() || '?';
  }

  function levelColor(level) {
    return { low: '#16a34a', medium: '#d97706', high: '#ea580c', critical: '#dc2626' }[level] || '#6b7280';
  }

  function scoreColor(score) {
    if (score >= 70) return '#dc2626';
    if (score >= 50) return '#ea580c';
    if (score >= 30) return '#d97706';
    return '#16a34a';
  }

  /* ---- load data -------------------------------------------------------
     Tries window.PA_DATA (set by inline script after #pa-data element),
     then falls back to parsing #pa-data directly.
  ----------------------------------------------------------------------- */
  var DATA = (window.PA_DATA && typeof window.PA_DATA === 'object') ? window.PA_DATA : null;
  if (!DATA) {
    try {
      var _el = document.getElementById('pa-data');
      DATA = _el ? JSON.parse(_el.textContent || _el.innerHTML || '{}') : {};
    } catch (e) { DATA = {}; }
  }
  DATA.kpis      = DATA.kpis      || { total: 0, at_risk: 0, high_critical: 0, avg_score: 0, safe: 0 };
  DATA.dist      = DATA.dist      || { low: 0, medium: 0, high: 0, critical: 0 };
  DATA.employees = DATA.employees || [];
  DATA.by_dept   = DATA.by_dept   || [];
  DATA.trend     = DATA.trend     || [];

  /* ---- KPIs ------------------------------------------------------------- */
  function renderKpis(kpis) {
    function set(id, val) {
      var el = $('#' + id);
      if (el) el.textContent = val;
    }
    set('kpi-total',        kpis.total);
    set('kpi-at-risk',      kpis.at_risk);
    set('kpi-high-critical', kpis.high_critical);
    set('kpi-avg-score',    kpis.avg_score);
    set('kpi-safe',         kpis.safe);
  }

  /* ---- Donut chart ------------------------------------------------------ */
  function renderDonut(dist, total) {
    var donutBig = $('#donut-big');
    if (donutBig) donutBig.textContent = total;

    var ctx = $('#chart-donut');
    if (!ctx || !window.Chart) return;

    var labels  = ['Low', 'Medium', 'High', 'Critical'];
    var values  = [dist.low, dist.medium, dist.high, dist.critical];
    var colors  = ['#16a34a', '#d97706', '#ea580c', '#dc2626'];
    var borders = ['#15803d', '#b45309', '#c2410c', '#b91c1c'];

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data:            values,
          backgroundColor: colors,
          borderColor:     borders,
          borderWidth:     2,
          hoverOffset:     6,
        }],
      },
      options: {
        cutout: '72%',
        plugins: {
          legend:  { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var pct = total ? Math.round(ctx.parsed / total * 100) : 0;
                return ' ' + ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
              },
            },
          },
        },
      },
    });

    var legend = $('#donut-legend');
    if (!legend) return;
    legend.innerHTML = labels.map(function (lbl, i) {
      return '<div class="pa-legend-item">' +
        '<div class="pa-legend-left">' +
        '<div class="pa-legend-dot" style="background:' + colors[i] + '"></div>' +
        '<span class="pa-legend-name">' + lbl + '</span>' +
        '</div>' +
        '<span class="pa-legend-count">' + values[i] + '</span>' +
        '</div>';
    }).join('');
  }

  /* ---- Bar chart (dept) ------------------------------------------------- */
  function renderBar(byDept) {
    var ctx = $('#chart-bar');
    if (!ctx || !window.Chart || !byDept.length) return;

    var labels = byDept.map(function (d) { return d.name; });
    var scores = byDept.map(function (d) { return d.avg_score; });
    var barColors = scores.map(scoreColor);

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label:           'Avg Risk Score',
          data:            scores,
          backgroundColor: barColors.map(function (c) { return c + '33'; }),
          borderColor:     barColors,
          borderWidth:     1.5,
          borderRadius:    4,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive:  true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: function (ctx) {
                var dept = byDept[ctx.dataIndex];
                return 'Employees: ' + dept.count + ' · High/Critical: ' + dept.high_count;
              },
            },
          },
        },
        scales: {
          x: {
            grid:   { color: 'rgba(0,0,0,0.06)' },
            ticks:  { color: '#9ca3af', font: { size: 11 } },
            max:    100,
          },
          y: {
            grid:   { display: false },
            ticks:  { color: '#9ca3af', font: { size: 11 } },
          },
        },
      },
    });
  }

  /* ---- Trend line chart ------------------------------------------------- */
  function renderTrend(trend) {
    var ctx    = $('#chart-trend');
    var empty  = $('#trend-empty');

    if (trend.length < 2) {
      if (ctx)   ctx.style.display = 'none';
      if (empty) empty.style.display = 'flex';
      return;
    }

    if (!ctx || !window.Chart) return;

    var labels = trend.map(function (t) { return t.label; });
    var values = trend.map(function (t) { return t.avg; });

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label:                'Avg Risk Score',
          data:                 values,
          borderColor:          '#7c3aed',
          backgroundColor:      'rgba(124,58,237,0.08)',
          borderWidth:          2,
          pointRadius:          5,
          pointBackgroundColor: '#7c3aed',
          pointBorderColor:     '#ffffff',
          pointBorderWidth:     2,
          fill:                 true,
          tension:              0.35,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            grid:  { color: 'rgba(0,0,0,0.06)' },
            ticks: { color: '#9ca3af', font: { size: 11 } },
          },
          y: {
            grid:     { color: 'rgba(0,0,0,0.06)' },
            ticks:    { color: '#9ca3af', font: { size: 11 } },
            min:      0,
            max:      100,
          },
        },
      },
    });
  }

  /* ---- Table rendering -------------------------------------------------- */
  var PAGE_SIZE = 20;
  var currentFilter = 'all';
  var currentSearch = '';
  var sortCol  = 'risk_score';
  var sortAsc  = false;
  var currentPage = 1;

  function filteredRows() {
    return DATA.employees.filter(function (emp) {
      if (currentFilter !== 'all' && emp.risk_level !== currentFilter) return false;
      if (currentSearch) {
        var q = currentSearch.toLowerCase();
        return (emp.name || '').toLowerCase().includes(q) ||
               (emp.dept || '').toLowerCase().includes(q) ||
               (emp.job  || '').toLowerCase().includes(q);
      }
      return true;
    });
  }

  function sortedRows(rows) {
    return rows.slice().sort(function (a, b) {
      var av = a[sortCol];
      var bv = b[sortCol];
      if (typeof av === 'string') av = av.toLowerCase();
      if (typeof bv === 'string') bv = bv.toLowerCase();
      if (av < bv) return sortAsc ? -1 :  1;
      if (av > bv) return sortAsc ?  1 : -1;
      return 0;
    });
  }

  function renderTableRows(rows) {
    var body = $('#pa-table-body');
    if (!body) return;

    var start = (currentPage - 1) * PAGE_SIZE;
    var page  = rows.slice(start, start + PAGE_SIZE);

    if (!page.length) {
      body.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted);font-size:13px">No employees match the current filter.</td></tr>';
      return;
    }

    body.innerHTML = page.map(function (emp) {
      var avatarHtml = emp.avatar
        ? '<img src="' + emp.avatar + '" alt="" onerror="this.remove()">'
        : initials(emp.name);

      var scoreWidth = Math.min(100, emp.risk_score) + '%';

      return '<tr data-emp-id="' + emp.id + '" style="cursor:pointer">' +
        '<td>' +
          '<div class="pa-emp-cell">' +
            '<div class="pa-emp-avatar">' + avatarHtml + '</div>' +
            '<div>' +
              '<div class="pa-emp-name">' + escHtml(emp.name) + '</div>' +
              '<div class="pa-emp-job">' + escHtml(emp.job || '—') + '</div>' +
            '</div>' +
          '</div>' +
        '</td>' +
        '<td style="color:var(--text-secondary);font-size:12px">' + escHtml(emp.dept) + '</td>' +
        '<td style="color:var(--text-secondary);font-size:12px">' + tenureLabel(emp.tenure_months) + '</td>' +
        '<td>' +
          '<div class="pa-score-cell">' +
            '<div class="pa-score-bar-wrap">' +
              '<span class="pa-score-num" style="color:' + scoreColor(emp.risk_score) + '">' + emp.risk_score + '</span>' +
              '<div class="pa-score-bar">' +
                '<div class="pa-score-fill pa-fill-' + emp.risk_level + '" style="width:' + scoreWidth + '"></div>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</td>' +
        '<td><span class="pa-level-badge pa-level-' + emp.risk_level + '">' + emp.risk_level + '</span></td>' +
        '<td><span class="pa-driver-chip">' + escHtml(emp.top_factor) + '</span></td>' +
        '<td>' +
          '<div class="pa-action-btn-group">' +
            '<button class="pa-assess-action-btn ' + (emp.assessed ? 'is-done' : 'is-pending') +
              '" data-assess-id="' + emp.id + '">' +
              (emp.assessed
                ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/></svg>Update'
                : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>Assess') +
            '</button>' +
            '<button class="pa-action-btn pa-detail-btn' + (emp.assessed ? '' : ' pa-detail-btn-locked') +
              '" data-emp-id="' + emp.id + '" ' + (emp.assessed ? '' : 'title="Complete HR Assessment first" tabindex="-1"') + '>' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
              'Details' +
            '</button>' +
          '</div>' +
        '</td>' +
        '</tr>';
    }).join('');

    // attach assess button clicks
    $$('.pa-assess-action-btn', body).forEach(function (btn) {
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        var empId = parseInt(btn.dataset.assessId, 10);
        var emp = DATA.employees.find(function (e) { return e.id === empId; });
        if (emp) openAssessModal(emp);
      });
    });

    // attach detail button clicks (assessed-only)
    $$('.pa-detail-btn:not(.pa-detail-btn-locked)', body).forEach(function (btn) {
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        var empId = parseInt(btn.dataset.empId, 10);
        var emp = DATA.employees.find(function (e) { return e.id === empId; });
        if (emp) openModal(emp);
      });
    });
  }

  function renderPagination(total) {
    var pages   = Math.ceil(total / PAGE_SIZE);
    var pag     = $('#pa-pagination');
    var showing = $('#pa-showing-label');
    var count   = $('#table-count');

    var start = (currentPage - 1) * PAGE_SIZE + 1;
    var end   = Math.min(currentPage * PAGE_SIZE, total);

    if (showing) {
      showing.textContent = total
        ? 'Showing ' + start + '–' + end + ' of ' + total
        : 'No results';
    }
    if (count) {
      count.textContent = total + ' employee' + (total !== 1 ? 's' : '');
    }

    if (!pag) return;
    if (pages <= 1) { pag.innerHTML = ''; return; }

    var html = '';
    if (currentPage > 1) {
      html += '<button class="pa-page-btn" data-page="' + (currentPage - 1) + '">‹</button>';
    }
    for (var i = 1; i <= pages; i++) {
      html += '<button class="pa-page-btn' + (i === currentPage ? ' is-active' : '') + '" data-page="' + i + '">' + i + '</button>';
    }
    if (currentPage < pages) {
      html += '<button class="pa-page-btn" data-page="' + (currentPage + 1) + '">›</button>';
    }
    pag.innerHTML = html;

    $$('.pa-page-btn', pag).forEach(function (btn) {
      btn.addEventListener('click', function () {
        currentPage = parseInt(btn.dataset.page, 10);
        refresh();
      });
    });
  }

  function refresh() {
    var rows    = filteredRows();
    var sorted  = sortedRows(rows);
    renderTableRows(sorted);
    renderPagination(sorted.length);
  }

  /* ---- Sort ------------------------------------------------------------- */
  $$('.pa-sortable').forEach(function (th) {
    th.addEventListener('click', function () {
      var col = th.dataset.col;
      if (sortCol === col) {
        sortAsc = !sortAsc;
      } else {
        sortCol = col;
        sortAsc = false;
      }
      $$('.pa-sortable').forEach(function (t) {
        t.classList.remove('pa-sort-active', 'pa-sort-asc', 'pa-sort-desc');
      });
      th.classList.add('pa-sort-active', sortAsc ? 'pa-sort-asc' : 'pa-sort-desc');
      currentPage = 1;
      refresh();
    });
  });

  /* ---- Search ----------------------------------------------------------- */
  var searchInput = $('#pa-search');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      currentSearch = searchInput.value.trim();
      currentPage   = 1;
      refresh();
    });
  }

  /* ---- Filter buttons --------------------------------------------------- */
  $$('.pa-filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      currentFilter = btn.dataset.filter;
      $$('.pa-filter-btn').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      currentPage = 1;
      refresh();
    });
  });

  /* ---- Modal ------------------------------------------------------------ */
  function openModal(emp) {
    var overlay = $('#pa-modal');
    if (!overlay) return;

    // Avatar
    var avatarWrap = $('#modal-avatar-wrap');
    if (avatarWrap) {
      avatarWrap.innerHTML = emp.avatar
        ? '<img src="' + emp.avatar + '" alt="" onerror="this.parentElement.textContent=\'' + initials(emp.name) + '\'">'
        : initials(emp.name);
    }

    setText('modal-name',   emp.name);
    setText('modal-job',    emp.job || '—');
    setText('modal-dept',   emp.dept || '—');
    setText('modal-tenure', tenureLabel(emp.tenure_months));
    setText('modal-age',    emp.age ? emp.age + ' years' : '—');
    setText('modal-driver', emp.top_factor);

    // Score value
    setText('modal-score-val', emp.risk_score);

    // Ring arc animation
    var arc = $('#modal-ring-arc');
    if (arc) {
      var circumference = 314; // 2 * π * 50
      var offset = circumference - (emp.risk_score / 100) * circumference;
      arc.style.strokeDashoffset = offset;
      arc.style.stroke = scoreColor(emp.risk_score);
    }

    // Level badge
    var badge = $('#modal-level-badge');
    if (badge) {
      badge.innerHTML = '<span class="pa-level-badge pa-level-' + emp.risk_level + '">' + emp.risk_level + '</span>';
    }

    // Factor bars
    var factorBars = $('#modal-factor-bars');
    if (factorBars && emp.factors) {
      factorBars.innerHTML = Object.keys(emp.factors).map(function (label) {
        var val   = emp.factors[label];
        var color = scoreColor(val);
        return '<div class="pa-factor-row">' +
          '<span class="pa-factor-label">' + escHtml(label) + '</span>' +
          '<div class="pa-factor-bar"><div class="pa-factor-fill" style="width:' + val + '%;background:' + color + '"></div></div>' +
          '<span class="pa-factor-val" style="color:' + color + '">' + Math.round(val) + '</span>' +
          '</div>';
      }).join('');
    }

    // Recommendations
    var recsList = $('#modal-recs-list');
    if (recsList) {
      var recs = emp.recommendations || [];
      if (recs.length) {
        recsList.innerHTML = recs.map(function (rec) {
          return '<div class="pa-rec-item">' +
            '<div class="pa-rec-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></svg></div>' +
            '<div class="pa-rec-text">' + escHtml(rec) + '</div>' +
            '</div>';
        }).join('');
      } else {
        recsList.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px 0">No specific recommendations at this time.</div>';
      }
    }

    // Employee link
    var empLink = $('#modal-emp-link');
    if (empLink) empLink.href = '/odoo/employees/' + emp.id;

    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    var overlay = $('#pa-modal');
    if (overlay) overlay.style.display = 'none';
    document.body.style.overflow = '';
  }

  var closeBtn = $('#pa-modal-close');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  var overlay = $('#pa-modal');
  if (overlay) {
    overlay.addEventListener('click', function (ev) {
      if (ev.target === overlay) closeModal();
    });
  }

  /* ---- Assessment modal ------------------------------------------------- */
  var currentAssessEmp = null;

  function computeAssessPreviewScore(autoScore) {
    var form = document.getElementById('pa-assess-form');
    if (!form) return autoScore;
    var score = 50.0;
    function ratingVal(name) {
      var inp = form.querySelector('input[name="' + name + '"]');
      return inp ? parseInt(inp.value, 10) || 3 : 3;
    }
    function boolVal(name) {
      var inp = form.querySelector('input[name="' + name + '"]');
      return inp && inp.value === 'true';
    }
    score -= (ratingVal('q_engagement') - 3) * 8.0;
    score -= (ratingVal('q_salary_satisfaction') - 3) * 5.0;
    score -= (ratingVal('q_career_growth') - 3) * 5.0;
    score -= (ratingVal('q_manager_relation') - 3) * 3.0;
    score -= (ratingVal('q_retention_confidence') - 3) * 10.0;
    if (boolVal('q_job_hunting'))      score += 25.0;
    if (boolVal('q_recent_promotion')) score -= 15.0;
    if (boolVal('q_burnout_risk'))     score += 10.0;
    score = Math.max(0, Math.min(100, Math.round(score * 10) / 10));
    var blended = Math.round((0.5 * autoScore + 0.5 * score) * 10) / 10;
    return blended;
  }

  function updateAssessPreview() {
    var emp = currentAssessEmp;
    if (!emp) return;
    var blended = computeAssessPreviewScore(emp.auto_score !== undefined ? emp.auto_score : emp.risk_score);
    var scoreEl = document.getElementById('assess-preview-score');
    var levelEl = document.getElementById('assess-preview-level');
    if (scoreEl) {
      scoreEl.textContent = blended;
      scoreEl.style.color = scoreColor(blended);
    }
    if (levelEl) {
      var lv = blended >= 70 ? 'critical' : blended >= 50 ? 'high' : blended >= 30 ? 'medium' : 'low';
      levelEl.textContent = lv.charAt(0).toUpperCase() + lv.slice(1);
      levelEl.className = 'pa-preview-level';
      levelEl.style.background = { low: '#dcfce7', medium: '#fef3c7', high: '#ffedd5', critical: '#fee2e2' }[lv] || '';
      levelEl.style.color = { low: '#16a34a', medium: '#d97706', high: '#ea580c', critical: '#dc2626' }[lv] || '';
    }
  }

  function setStars(groupEl, val) {
    $$('.pa-star', groupEl).forEach(function (star) {
      var sv = parseInt(star.dataset.val, 10);
      if (sv <= val) {
        star.classList.add('is-filled');
      } else {
        star.classList.remove('is-filled');
      }
    });
    var hidden = groupEl.parentElement ? groupEl.parentElement.querySelector('.pa-rate-val') : null;
    if (hidden) hidden.value = val;
  }

  function openAssessModal(emp) {
    currentAssessEmp = emp;
    var overlay = document.getElementById('pa-assess-modal');
    if (!overlay) return;

    // Set employee identity
    var avEl = document.getElementById('assess-avatar');
    if (avEl) {
      avEl.innerHTML = emp.avatar
        ? '<img src="' + emp.avatar + '" alt="" onerror="this.parentElement.textContent=\'' + initials(emp.name) + '\'">'
        : initials(emp.name);
    }
    setText('assess-emp-name', emp.name);
    setText('assess-emp-job', emp.job || '—');

    var hiddenId = document.getElementById('assess-emp-id');
    if (hiddenId) hiddenId.value = emp.id;

    // Pre-fill with existing answers if assessed
    var ans = emp.assess_answers || {};

    // Reset all star groups to default (3) first
    $$('.pa-stars').forEach(function (grp) { setStars(grp, ans[grp.dataset.name] || 3); });

    // Reset Yes/No buttons
    $$('.pa-yn-btn').forEach(function (btn) { btn.classList.remove('is-active'); });
    function setYN(field, val) {
      var wrap = document.querySelector('[data-field="' + field + '"][data-val="' + (val ? 'true' : 'false') + '"]');
      if (wrap) wrap.classList.add('is-active');
      var inp = document.querySelector('input[name="' + field + '"]');
      if (inp) inp.value = val ? 'true' : 'false';
    }
    setYN('q_job_hunting',      !!ans.q_job_hunting);
    setYN('q_recent_promotion', !!ans.q_recent_promotion);
    setYN('q_burnout_risk',     !!ans.q_burnout_risk);

    // Notes
    var notesEl = document.getElementById('assess-notes');
    if (notesEl) notesEl.value = ans.notes || '';

    // Update preview
    updateAssessPreview();

    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeAssessModal() {
    var overlay = document.getElementById('pa-assess-modal');
    if (overlay) overlay.style.display = 'none';
    document.body.style.overflow = '';
    currentAssessEmp = null;
  }

  // Star click listeners (delegated on document since form is static HTML)
  document.addEventListener('click', function (ev) {
    var star = ev.target.closest('.pa-star');
    if (!star) return;
    var grp = star.closest('.pa-stars');
    if (!grp) return;
    setStars(grp, parseInt(star.dataset.val, 10));
    updateAssessPreview();
  });

  // Yes/No button listeners
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('.pa-yn-btn');
    if (!btn) return;
    var field = btn.dataset.field;
    var val   = btn.dataset.val;
    // deactivate sibling
    document.querySelectorAll('.pa-yn-btn[data-field="' + field + '"]').forEach(function (b) {
      b.classList.remove('is-active');
    });
    btn.classList.add('is-active');
    var inp = document.querySelector('input[name="' + field + '"]');
    if (inp) inp.value = val;
    updateAssessPreview();
  });

  // Close assess modal
  var assessCloseBtn = document.getElementById('pa-assess-close');
  if (assessCloseBtn) assessCloseBtn.addEventListener('click', closeAssessModal);

  var assessCancelBtn = document.getElementById('pa-assess-cancel');
  if (assessCancelBtn) assessCancelBtn.addEventListener('click', closeAssessModal);

  var assessOverlay = document.getElementById('pa-assess-modal');
  if (assessOverlay) {
    assessOverlay.addEventListener('click', function (ev) {
      if (ev.target === assessOverlay) closeAssessModal();
    });
  }

  // Escape closes whichever modal is open
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    var assessOverlayEl = document.getElementById('pa-assess-modal');
    if (assessOverlayEl && assessOverlayEl.style.display !== 'none') {
      closeAssessModal();
    } else {
      closeModal();
    }
  });

  // Assessment form submit
  var assessForm = document.getElementById('pa-assess-form');
  if (assessForm) {
    assessForm.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var saving = document.getElementById('pa-assess-saving');
      if (saving) saving.style.display = 'flex';

      var data = new FormData(assessForm);
      var params = new URLSearchParams();
      data.forEach(function (val, key) { params.append(key, val); });

      fetch('/hrsd/attrition/assess/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      })
        .then(function (res) { return res.json(); })
        .then(function (result) {
          if (saving) saving.style.display = 'none';
          if (!result.ok || result.error) {
            alert('Error saving assessment: ' + (result.error || 'Unknown error'));
            return;
          }
          // Update employee data in-place
          var empId = result.employee_id;
          var idx = DATA.employees.findIndex(function (e) { return e.id === empId; });
          if (idx >= 0) {
            DATA.employees[idx].risk_score    = result.blended_score;
            DATA.employees[idx].auto_score    = result.auto_score;
            DATA.employees[idx].risk_level    = result.risk_level;
            DATA.employees[idx].assessed      = true;
            DATA.employees[idx].assessed_date = result.assessed_date;
            DATA.employees[idx].assess_answers = result.answers;
          }
          // Refresh table
          refresh();
          closeAssessModal();
          // Auto-open detail modal for this employee
          var emp = DATA.employees[idx];
          if (emp) {
            setTimeout(function () { openModal(emp); }, 150);
          }
        })
        .catch(function (err) {
          if (saving) saving.style.display = 'none';
          alert('Network error. Please try again.');
          console.error(err);
        });
    });
  }

  /* ---- CSV export ------------------------------------------------------- */
  var exportBtn = $('#pa-export-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', function () {
      var rows = filteredRows();
      var cols = ['Name', 'Department', 'Job', 'Tenure (months)', 'Risk Score', 'Risk Level', 'Top Driver'];
      var csv  = [cols.join(',')];
      rows.forEach(function (emp) {
        csv.push([
          csvEsc(emp.name),
          csvEsc(emp.dept),
          csvEsc(emp.job),
          emp.tenure_months,
          emp.risk_score,
          emp.risk_level,
          csvEsc(emp.top_factor),
        ].join(','));
      });
      var blob = new Blob([csv.join('\n')], { type: 'text/csv' });
      var a    = document.createElement('a');
      a.href   = URL.createObjectURL(blob);
      a.download = 'attrition_risk_' + new Date().toISOString().slice(0, 10) + '.csv';
      a.click();
    });
  }

  /* ---- Utilities -------------------------------------------------------- */
  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = (val === null || val === undefined) ? '—' : val;
  }

  function escHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function csvEsc(val) {
    var s = String(val || '').replace(/"/g, '""');
    return /[",\n]/.test(s) ? '"' + s + '"' : s;
  }

  /* ---- Boot ------------------------------------------------------------- */
  function init() {
    renderKpis(DATA.kpis);
    renderDonut(DATA.dist, DATA.kpis.total);
    renderBar(DATA.by_dept);
    renderTrend(DATA.trend);
    refresh();
  }

  // Script is at end of <body>: DOM is built, DOMContentLoaded hasn't fired yet.
  // Use readyState guard to run once.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
