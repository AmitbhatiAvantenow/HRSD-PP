/* ==========================================================================
   Performance Appraisal — dashboard logic
   ========================================================================== */
(function () {
  "use strict";

  /* ---- helpers ---------------------------------------------------------- */
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

  function initials(name) {
    return (name || '').split(' ').filter(Boolean).slice(0, 2)
      .map(function (p) { return p[0]; }).join('').toUpperCase() || '?';
  }

  function titleize(str) {
    return String(str || '').split('_').map(function (w) {
      return w.charAt(0).toUpperCase() + w.slice(1);
    }).join(' ');
  }

  var BAND_COLORS = {
    outstanding:    '#7c3aed',
    exceeds:        '#2563eb',
    meets:          '#0d9488',
    below:          '#d97706',
    unsatisfactory: '#dc2626',
  };

  var BAND_LABELS = {
    outstanding: 'Outstanding',
    exceeds: 'Exceeds Expectations',
    meets: 'Meets Expectations',
    below: 'Below Expectations',
    unsatisfactory: 'Unsatisfactory',
  };

  var PERF_BUCKET = {
    outstanding: 'high', exceeds: 'high',
    meets: 'medium',
    below: 'low', unsatisfactory: 'low',
  };

  var STATUS_OPTIONS = [
    ['not_started', 'Not Started'],
    ['in_progress', 'In Progress'],
    ['achieved', 'Achieved'],
    ['partially_achieved', 'Partially Achieved'],
    ['not_achieved', 'Not Achieved'],
  ];

  function scoreColor(score) {
    if (score >= 90) return BAND_COLORS.outstanding;
    if (score >= 75) return BAND_COLORS.exceeds;
    if (score >= 60) return BAND_COLORS.meets;
    if (score >= 40) return BAND_COLORS.below;
    return BAND_COLORS.unsatisfactory;
  }

  /* ---- load data ---------------------------------------------------------
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
  DATA.kpis       = DATA.kpis       || { total: 0, completed: 0, in_progress: 0, overdue: 0, avg_score: 0 };
  DATA.dist       = DATA.dist       || { outstanding: 0, exceeds: 0, meets: 0, below: 0, unsatisfactory: 0 };
  DATA.nine_box   = DATA.nine_box   || {};
  DATA.appraisals = DATA.appraisals || [];
  DATA.by_dept    = DATA.by_dept    || [];

  /* ---- KPIs --------------------------------------------------------------- */
  function renderKpis(kpis) {
    function set(id, val) {
      var el = $('#' + id);
      if (el) el.textContent = val;
    }
    set('kpi-total',       kpis.total);
    set('kpi-completed',   kpis.completed);
    set('kpi-in-progress', kpis.in_progress);
    set('kpi-overdue',     kpis.overdue);
    set('kpi-avg-score',   kpis.avg_score);
  }

  /* ---- Donut chart (performance bands) ------------------------------------ */
  function renderDonut(dist, total) {
    var donutBig = $('#donut-big');
    if (donutBig) donutBig.textContent = total;

    var ctx = $('#chart-donut');
    if (!ctx || !window.Chart) return;

    var keys   = ['outstanding', 'exceeds', 'meets', 'below', 'unsatisfactory'];
    var labels = keys.map(function (k) { return BAND_LABELS[k]; });
    var values = keys.map(function (k) { return dist[k] || 0; });
    var colors = keys.map(function (k) { return BAND_COLORS[k]; });

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data:            values,
          backgroundColor: colors,
          borderColor:     '#ffffff',
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

  /* ---- 9-Box Talent Grid --------------------------------------------------- */
  var NINE_BOX_LABELS = {
    high_high:     'Star',
    high_medium:   'High Performer',
    high_low:      'Solid Professional',
    medium_high:   'High Potential',
    medium_medium: 'Core Performer',
    medium_low:    'Effective',
    low_high:      'Rough Diamond',
    low_medium:    'Inconsistent Performer',
    low_low:       'Underperformer',
  };

  var nineBoxFilter = null;

  function renderNineBox(nineBox) {
    var grid = $('#ninebox-grid');
    if (!grid) return;

    var perfOrder = ['high', 'medium', 'low'];
    var potOrder  = ['low', 'medium', 'high'];

    var html = '';
    perfOrder.forEach(function (perf) {
      potOrder.forEach(function (pot) {
        var key   = perf + '_' + pot;
        var count = nineBox[key] || 0;
        var cls   = key === 'high_high' ? 'is-star' : key === 'low_low' ? 'is-risk' : key === 'medium_medium' ? 'is-core' : '';
        html += '<div class="pa-ninebox-cell ' + cls + (count ? '' : ' is-empty') + '" data-key="' + key + '">' +
          '<div class="pa-ninebox-cell-label">' + NINE_BOX_LABELS[key] + '</div>' +
          '<div class="pa-ninebox-cell-count">' + count + '</div>' +
          '</div>';
      });
    });
    grid.innerHTML = html;

    $$('.pa-ninebox-cell', grid).forEach(function (cell) {
      cell.addEventListener('click', function () {
        var key = cell.dataset.key;
        $$('.pa-ninebox-cell', grid).forEach(function (c) { c.style.outline = ''; });
        if (nineBoxFilter === key) {
          nineBoxFilter = null;
        } else {
          nineBoxFilter = key;
          cell.style.outline = '2px solid var(--purple)';
        }
        currentPage = 1;
        refresh();
      });
    });
  }

  /* ---- Bar chart (dept avg score) ------------------------------------------ */
  function renderBar(byDept) {
    var ctx = $('#chart-bar');
    if (!ctx || !window.Chart || !byDept.length) return;

    var labels    = byDept.map(function (d) { return d.name; });
    var scores    = byDept.map(function (d) { return d.avg_score; });
    var barColors = scores.map(scoreColor);

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label:           'Avg Final Score',
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
                return 'Appraisals: ' + dept.count;
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

  /* ---- Table rendering ------------------------------------------------------ */
  var PAGE_SIZE = 20;
  var currentFilter = 'all';
  var currentSearch = '';
  var sortCol  = 'overall_score';
  var sortAsc  = false;
  var currentPage = 1;

  function filteredRows() {
    return DATA.appraisals.filter(function (a) {
      if (currentFilter !== 'all' && a.state !== currentFilter) return false;
      if (nineBoxFilter) {
        var perf = PERF_BUCKET[a.performance_band] || 'medium';
        var key  = perf + '_' + (a.potential || 'medium');
        if (key !== nineBoxFilter) return false;
      }
      if (currentSearch) {
        var q = currentSearch.toLowerCase();
        return (a.name || '').toLowerCase().includes(q) ||
               (a.dept || '').toLowerCase().includes(q) ||
               (a.job  || '').toLowerCase().includes(q);
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

  function actionButtonHtml(a) {
    if (a.state === 'draft') {
      return '<button class="pa-assess-action-btn is-pending" data-start-id="' + a.id + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>Start Review</button>';
    }
    if (a.state === 'self_assessment') {
      return '<button class="pa-assess-action-btn is-pending" data-self-id="' + a.id + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>Self-Assess</button>';
    }
    if (a.state === 'manager_review' || a.state === 'calibration') {
      return '<button class="pa-assess-action-btn is-pending" data-mgr-id="' + a.id + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/></svg>Manager Review</button>';
    }
    return '<span class="pa-assess-action-btn is-done"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/></svg>Completed</span>';
  }

  function renderTableRows(rows) {
    var body = $('#pa-table-body');
    if (!body) return;

    var start = (currentPage - 1) * PAGE_SIZE;
    var page  = rows.slice(start, start + PAGE_SIZE);

    if (!page.length) {
      body.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted);font-size:13px">No appraisals match the current filter.</td></tr>';
      return;
    }

    body.innerHTML = page.map(function (a) {
      var avatarHtml = a.avatar
        ? '<img src="' + a.avatar + '" alt="" onerror="this.remove()">'
        : initials(a.name);

      var scoreWidth = Math.min(100, a.overall_score) + '%';

      return '<tr data-appraisal-id="' + a.id + '" style="cursor:pointer">' +
        '<td>' +
          '<div class="pa-emp-cell">' +
            '<div class="pa-emp-avatar">' + avatarHtml + '</div>' +
            '<div>' +
              '<div class="pa-emp-name">' + escHtml(a.name) + '</div>' +
              '<div class="pa-emp-job">' + escHtml(a.job || '—') + '</div>' +
            '</div>' +
          '</div>' +
        '</td>' +
        '<td style="color:var(--text-secondary);font-size:12px">' + escHtml(a.dept) + '</td>' +
        '<td><span class="pa-cycle-chip">' + titleize(a.cycle_type) + '</span></td>' +
        '<td><span class="pa-level-badge pa-state-' + a.state + '">' + escHtml(a.state_label) + '</span></td>' +
        '<td>' +
          '<div class="pa-score-cell">' +
            '<div class="pa-score-bar-wrap">' +
              '<span class="pa-score-num" style="color:' + scoreColor(a.overall_score) + '">' + a.overall_score + '</span>' +
              '<div class="pa-score-bar">' +
                '<div class="pa-score-fill" style="width:' + scoreWidth + ';background:' + scoreColor(a.overall_score) + '"></div>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</td>' +
        '<td><span class="pa-level-badge pa-band-' + a.performance_band + '">' + escHtml(a.band_label) + '</span></td>' +
        '<td>' +
          '<div class="pa-action-btn-group">' +
            actionButtonHtml(a) +
            '<button class="pa-action-btn pa-detail-btn" data-detail-id="' + a.id + '">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
              'Details' +
            '</button>' +
          '</div>' +
        '</td>' +
        '</tr>';
    }).join('');

    $$('[data-start-id]', body).forEach(function (btn) {
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        startReview(parseInt(btn.dataset.startId, 10));
      });
    });
    $$('[data-self-id]', body).forEach(function (btn) {
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        var a = DATA.appraisals.find(function (x) { return x.id === parseInt(btn.dataset.selfId, 10); });
        if (a) openSelfModal(a);
      });
    });
    $$('[data-mgr-id]', body).forEach(function (btn) {
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        var a = DATA.appraisals.find(function (x) { return x.id === parseInt(btn.dataset.mgrId, 10); });
        if (a) openMgrModal(a);
      });
    });
    $$('[data-detail-id]', body).forEach(function (btn) {
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        var a = DATA.appraisals.find(function (x) { return x.id === parseInt(btn.dataset.detailId, 10); });
        if (a) openModal(a);
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
      count.textContent = total + ' appraisal' + (total !== 1 ? 's' : '');
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
    var rows   = filteredRows();
    var sorted = sortedRows(rows);
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

  /* ---- Filter buttons ----------------------------------------------------- */
  $$('.pa-filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      currentFilter = btn.dataset.filter;
      $$('.pa-filter-btn').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      currentPage = 1;
      refresh();
    });
  });

  /* ---- Detail modal -------------------------------------------------------- */
  function dualBarHtml(name, meta, selfVal, mgrVal) {
    return '<div class="pa-dual-row">' +
      '<div class="pa-dual-row-head"><span class="pa-dual-name">' + escHtml(name) + '</span><span class="pa-dual-weight">' + escHtml(meta) + '</span></div>' +
      '<div class="pa-dual-bar-line">' +
        '<span class="pa-dual-bar-tag">Self</span>' +
        '<div class="pa-dual-bar-track"><div class="pa-dual-bar-fill is-self" style="width:' + selfVal + '%"></div></div>' +
        '<span class="pa-dual-bar-val">' + Math.round(selfVal) + '%</span>' +
      '</div>' +
      '<div class="pa-dual-bar-line">' +
        '<span class="pa-dual-bar-tag">Manager</span>' +
        '<div class="pa-dual-bar-track"><div class="pa-dual-bar-fill is-manager" style="width:' + mgrVal + '%"></div></div>' +
        '<span class="pa-dual-bar-val">' + Math.round(mgrVal) + '%</span>' +
      '</div>' +
      '</div>';
  }

  function openModal(a) {
    var overlay = $('#pa-modal');
    if (!overlay) return;

    var avatarWrap = $('#modal-avatar-wrap');
    if (avatarWrap) {
      avatarWrap.innerHTML = a.avatar
        ? '<img src="' + a.avatar + '" alt="" onerror="this.parentElement.textContent=\'' + initials(a.name) + '\'">'
        : initials(a.name);
    }

    setText('modal-name', a.name);
    setText('modal-job',  a.job || '—');
    setText('modal-dept', a.dept || '—');
    setText('modal-score-val', a.overall_score);
    setText('modal-cycle', titleize(a.cycle_type));
    setText('modal-state', a.state_label);
    setText('modal-ninebox', a.nine_box_label);

    var arc = $('#modal-ring-arc');
    if (arc) {
      var circumference = 314;
      var offset = circumference - (Math.min(100, a.overall_score) / 100) * circumference;
      arc.style.strokeDashoffset = offset;
      arc.style.stroke = scoreColor(a.overall_score);
    }

    var badge = $('#modal-band-badge');
    if (badge) {
      badge.innerHTML = '<span class="pa-level-badge pa-band-' + a.performance_band + '">' + escHtml(a.band_label) + '</span>';
    }

    var goalsEl = $('#modal-goals');
    if (goalsEl) {
      if (a.goals.length) {
        goalsEl.innerHTML = a.goals.map(function (g) {
          return dualBarHtml(g.name, 'Weight ' + g.weight + '%' + (g.target_value ? ' · ' + g.target_value : ''), g.self_progress, g.manager_progress);
        }).join('');
      } else {
        goalsEl.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:6px 0">No goals defined for this appraisal.</div>';
      }
    }

    var compsEl = $('#modal-comps');
    if (compsEl) {
      if (a.competencies.length) {
        compsEl.innerHTML = a.competencies.map(function (c) {
          return dualBarHtml(c.name_label, '', c.self_score * 20, c.manager_score * 20);
        }).join('');
      } else {
        compsEl.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:6px 0">No competencies rated yet.</div>';
      }
    }

    var fbEl = $('#modal-feedback');
    if (fbEl) {
      if (a.feedback.length) {
        fbEl.innerHTML = a.feedback.map(function (f) {
          var stars = '★★★★★'.slice(0, f.rating) + '☆☆☆☆☆'.slice(0, 5 - f.rating);
          return '<div class="pa-rec-item">' +
            '<div class="pa-rec-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/></svg></div>' +
            '<div class="pa-rec-text"><strong>' + escHtml(f.reviewer) + '</strong> (' + titleize(f.relation) + ') — ' + stars + '<br/>' + escHtml(f.comments) + '</div>' +
            '</div>';
        }).join('');
      } else {
        fbEl.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px 0">No 360° feedback collected yet.</div>';
      }
    }

    var empLink = $('#modal-emp-link');
    if (empLink) empLink.href = '/odoo/employees/' + a.employee_id;

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
  var modalOverlay = $('#pa-modal');
  if (modalOverlay) {
    modalOverlay.addEventListener('click', function (ev) { if (ev.target === modalOverlay) closeModal(); });
  }

  /* ---- Star rating helper (generic, used by self & manager forms) --------- */
  function starsHtml(compId, value) {
    var html = '<div class="pa-stars" data-comp-id="' + compId + '" data-value="' + value + '">';
    for (var v = 1; v <= 5; v++) {
      html += '<button type="button" class="pa-star' + (v <= value ? ' is-filled' : '') + '" data-val="' + v + '">★</button>';
    }
    html += '</div>';
    return html;
  }

  document.addEventListener('click', function (ev) {
    var star = ev.target.closest('.pa-star');
    if (!star) return;
    var grp = star.closest('.pa-stars');
    if (!grp) return;
    var val = parseInt(star.dataset.val, 10);
    grp.dataset.value = val;
    $$('.pa-star', grp).forEach(function (s) {
      s.classList.toggle('is-filled', parseInt(s.dataset.val, 10) <= val);
    });
  });

  document.addEventListener('input', function (ev) {
    if (ev.target.matches('.pa-goalform-slider-row input[type="range"]')) {
      var row = ev.target.closest('.pa-goalform-slider-row');
      var lbl = row ? row.querySelector('.pa-goalform-slider-val') : null;
      if (lbl) lbl.textContent = ev.target.value + '%';
    }
  });

  /* ---- Self-assessment modal ------------------------------------------------ */
  function goalFormRowHtml(g, progressField, includeStatus) {
    var value = progressField === 'self' ? g.self_progress : g.manager_progress;
    var statusHtml = '';
    if (includeStatus) {
      statusHtml = '<div class="pa-goalform-status"><select class="goal-status-select">' +
        STATUS_OPTIONS.map(function (opt) {
          return '<option value="' + opt[0] + '"' + (opt[0] === g.status ? ' selected="selected"' : '') + '>' + opt[1] + '</option>';
        }).join('') + '</select></div>';
    }
    return '<div class="pa-goalform-row" data-goal-id="' + g.id + '">' +
      '<div class="pa-goalform-head">' +
        '<span class="pa-goalform-name">' + escHtml(g.name) + '</span>' +
        '<span class="pa-goalform-meta">Weight ' + g.weight + '%' + (g.target_value ? ' · ' + escHtml(g.target_value) : '') + '</span>' +
      '</div>' +
      '<div class="pa-goalform-slider-row">' +
        '<input type="range" min="0" max="100" value="' + value + '"/>' +
        '<span class="pa-goalform-slider-val">' + value + '%</span>' +
      '</div>' +
      statusHtml +
      '</div>';
  }

  var currentSelfAppraisal = null;

  function openSelfModal(a) {
    currentSelfAppraisal = a;
    var overlay = document.getElementById('pa-self-modal');
    if (!overlay) return;

    var avEl = document.getElementById('self-avatar');
    if (avEl) {
      avEl.innerHTML = a.avatar
        ? '<img src="' + a.avatar + '" alt="" onerror="this.parentElement.textContent=\'' + initials(a.name) + '\'">'
        : initials(a.name);
    }
    setText('self-emp-name', a.name);
    setText('self-emp-job', a.job || '—');
    document.getElementById('self-appraisal-id').value = a.id;

    var goalsContainer = document.getElementById('self-goals-container');
    if (goalsContainer) {
      goalsContainer.innerHTML = a.goals.length
        ? a.goals.map(function (g) { return goalFormRowHtml(g, 'self', false); }).join('')
        : '<div style="font-size:12px;color:var(--text-muted)">No goals defined.</div>';
    }

    var compsContainer = document.getElementById('self-comps-container');
    if (compsContainer) {
      compsContainer.innerHTML = a.competencies.length
        ? a.competencies.map(function (c) {
            return '<div class="pa-comp-row"><span class="pa-comp-name">' + escHtml(c.name_label) + '</span>' +
              starsHtml(c.id, c.self_score) + '</div>';
          }).join('')
        : '<div style="font-size:12px;color:var(--text-muted)">No competencies defined.</div>';
    }

    document.getElementById('self-comments').value = a.employee_comments || '';

    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeSelfModal() {
    var overlay = document.getElementById('pa-self-modal');
    if (overlay) overlay.style.display = 'none';
    document.body.style.overflow = '';
    currentSelfAppraisal = null;
  }

  var selfCloseBtn = document.getElementById('pa-self-close');
  if (selfCloseBtn) selfCloseBtn.addEventListener('click', closeSelfModal);
  var selfCancelBtn = document.getElementById('pa-self-cancel');
  if (selfCancelBtn) selfCancelBtn.addEventListener('click', closeSelfModal);
  var selfOverlay = document.getElementById('pa-self-modal');
  if (selfOverlay) {
    selfOverlay.addEventListener('click', function (ev) { if (ev.target === selfOverlay) closeSelfModal(); });
  }

  var selfForm = document.getElementById('pa-self-form');
  if (selfForm) {
    selfForm.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var saving = document.getElementById('pa-self-saving');
      if (saving) saving.style.display = 'flex';

      var appraisalId = parseInt(document.getElementById('self-appraisal-id').value, 10);
      var goals = $$('#self-goals-container .pa-goalform-row').map(function (row) {
        return {
          id: parseInt(row.dataset.goalId, 10),
          self_progress: parseInt(row.querySelector('input[type="range"]').value, 10),
        };
      });
      var competencies = $$('#self-comps-container .pa-stars').map(function (grp) {
        return { id: parseInt(grp.dataset.compId, 10), self_score: parseInt(grp.dataset.value, 10) };
      });
      var comments = document.getElementById('self-comments').value;

      fetch('/hrsd/appraisal/self-assess/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appraisal_id: appraisalId, goals: goals, competencies: competencies, comments: comments }),
      })
        .then(function (res) { return res.json(); })
        .then(function (result) {
          if (saving) saving.style.display = 'none';
          if (!result.ok) {
            alert('Error saving self-assessment: ' + (result.error || 'Unknown error'));
            return;
          }
          updateLocalAppraisal(result.appraisal);
          refresh();
          closeSelfModal();
        })
        .catch(function (err) {
          if (saving) saving.style.display = 'none';
          alert('Network error. Please try again.');
          console.error(err);
        });
    });
  }

  /* ---- Manager review modal -------------------------------------------------- */
  var currentMgrAppraisal = null;

  function openMgrModal(a) {
    currentMgrAppraisal = a;
    var overlay = document.getElementById('pa-mgr-modal');
    if (!overlay) return;

    var avEl = document.getElementById('mgr-avatar');
    if (avEl) {
      avEl.innerHTML = a.avatar
        ? '<img src="' + a.avatar + '" alt="" onerror="this.parentElement.textContent=\'' + initials(a.name) + '\'">'
        : initials(a.name);
    }
    setText('mgr-emp-name', a.name);
    setText('mgr-emp-job', a.job || '—');
    document.getElementById('mgr-appraisal-id').value = a.id;

    var goalsContainer = document.getElementById('mgr-goals-container');
    if (goalsContainer) {
      goalsContainer.innerHTML = a.goals.length
        ? a.goals.map(function (g) { return goalFormRowHtml(g, 'manager', true); }).join('')
        : '<div style="font-size:12px;color:var(--text-muted)">No goals defined.</div>';
    }

    var compsContainer = document.getElementById('mgr-comps-container');
    if (compsContainer) {
      compsContainer.innerHTML = a.competencies.length
        ? a.competencies.map(function (c) {
            return '<div class="pa-comp-row"><span class="pa-comp-name">' + escHtml(c.name_label) + '</span>' +
              starsHtml(c.id, c.manager_score) + '</div>';
          }).join('')
        : '<div style="font-size:12px;color:var(--text-muted)">No competencies defined.</div>';
    }

    var potential = a.potential || 'medium';
    document.getElementById('mgr-potential').value = potential;
    $$('#mgr-potential-group .pa-yn-btn').forEach(function (btn) {
      btn.classList.toggle('is-active', btn.dataset.potential === potential);
    });

    document.getElementById('mgr-strengths').value = a.strengths || '';
    document.getElementById('mgr-areas').value      = a.areas_of_improvement || '';
    document.getElementById('mgr-devplan').value     = a.development_plan || '';
    document.getElementById('mgr-comments').value    = a.manager_comments || '';

    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeMgrModal() {
    var overlay = document.getElementById('pa-mgr-modal');
    if (overlay) overlay.style.display = 'none';
    document.body.style.overflow = '';
    currentMgrAppraisal = null;
  }

  var mgrCloseBtn = document.getElementById('pa-mgr-close');
  if (mgrCloseBtn) mgrCloseBtn.addEventListener('click', closeMgrModal);
  var mgrCancelBtn = document.getElementById('pa-mgr-cancel');
  if (mgrCancelBtn) mgrCancelBtn.addEventListener('click', closeMgrModal);
  var mgrOverlay = document.getElementById('pa-mgr-modal');
  if (mgrOverlay) {
    mgrOverlay.addEventListener('click', function (ev) { if (ev.target === mgrOverlay) closeMgrModal(); });
  }

  $$('#mgr-potential-group .pa-yn-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      $$('#mgr-potential-group .pa-yn-btn').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      document.getElementById('mgr-potential').value = btn.dataset.potential;
    });
  });

  var mgrForm = document.getElementById('pa-mgr-form');
  if (mgrForm) {
    mgrForm.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var saving = document.getElementById('pa-mgr-saving');
      if (saving) saving.style.display = 'flex';

      var appraisalId = parseInt(document.getElementById('mgr-appraisal-id').value, 10);
      var goals = $$('#mgr-goals-container .pa-goalform-row').map(function (row) {
        var statusSel = row.querySelector('.goal-status-select');
        return {
          id: parseInt(row.dataset.goalId, 10),
          manager_progress: parseInt(row.querySelector('input[type="range"]').value, 10),
          status: statusSel ? statusSel.value : undefined,
        };
      });
      var competencies = $$('#mgr-comps-container .pa-stars').map(function (grp) {
        return { id: parseInt(grp.dataset.compId, 10), manager_score: parseInt(grp.dataset.value, 10) };
      });

      var payload = {
        appraisal_id: appraisalId,
        goals: goals,
        competencies: competencies,
        potential: document.getElementById('mgr-potential').value,
        strengths: document.getElementById('mgr-strengths').value,
        areas_of_improvement: document.getElementById('mgr-areas').value,
        development_plan: document.getElementById('mgr-devplan').value,
        manager_comments: document.getElementById('mgr-comments').value,
      };

      fetch('/hrsd/appraisal/manager-review/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then(function (res) { return res.json(); })
        .then(function (result) {
          if (saving) saving.style.display = 'none';
          if (!result.ok) {
            alert('Error saving manager review: ' + (result.error || 'Unknown error'));
            return;
          }
          updateLocalAppraisal(result.appraisal);
          refresh();
          closeMgrModal();
        })
        .catch(function (err) {
          if (saving) saving.style.display = 'none';
          alert('Network error. Please try again.');
          console.error(err);
        });
    });
  }

  /* ---- Quick "start review" action ------------------------------------------ */
  function startReview(appraisalId) {
    fetch('/hrsd/appraisal/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ appraisal_id: appraisalId }),
    })
      .then(function (res) { return res.json(); })
      .then(function (result) {
        if (!result.ok) {
          alert('Error starting review: ' + (result.error || 'Unknown error'));
          return;
        }
        updateLocalAppraisal(result.appraisal);
        refresh();
      })
      .catch(function (err) {
        alert('Network error. Please try again.');
        console.error(err);
      });
  }

  /* ---- Shared: patch in-memory data after a save --------------------------- */
  function updateLocalAppraisal(updated) {
    var idx = DATA.appraisals.findIndex(function (x) { return x.id === updated.id; });
    if (idx >= 0) DATA.appraisals[idx] = updated;
  }

  /* ---- Escape closes whichever modal is open -------------------------------- */
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    if (document.getElementById('pa-self-modal').style.display === 'flex') { closeSelfModal(); return; }
    if (document.getElementById('pa-mgr-modal').style.display === 'flex')  { closeMgrModal();  return; }
    closeModal();
  });

  /* ---- CSV export ------------------------------------------------------- */
  var exportBtn = $('#pa-export-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', function () {
      var rows = filteredRows();
      var cols = ['Name', 'Department', 'Cycle', 'Status', 'Self Score', 'Manager Score', 'Final Score', 'Band'];
      var csv  = [cols.join(',')];
      rows.forEach(function (a) {
        csv.push([
          csvEsc(a.name),
          csvEsc(a.dept),
          csvEsc(titleize(a.cycle_type)),
          csvEsc(a.state_label),
          a.self_score,
          a.manager_score,
          a.overall_score,
          csvEsc(a.band_label),
        ].join(','));
      });
      var blob = new Blob([csv.join('\n')], { type: 'text/csv' });
      var a2   = document.createElement('a');
      a2.href  = URL.createObjectURL(blob);
      a2.download = 'performance_appraisal_' + new Date().toISOString().slice(0, 10) + '.csv';
      a2.click();
    });
  }

  /* ---- Utilities -------------------------------------------------------- */
  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = (val === null || val === undefined || val === '') ? '—' : val;
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

  /* ---- Boot --------------------------------------------------------------- */
  function init() {
    renderKpis(DATA.kpis);
    renderDonut(DATA.dist, DATA.kpis.total);
    renderNineBox(DATA.nine_box);
    renderBar(DATA.by_dept);
    refresh();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
