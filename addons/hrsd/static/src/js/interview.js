/* =========================================================================
   AI Interview Questions — interview.js
   ========================================================================= */
(function () {
  'use strict';

  /* ── Utilities ─────────────────────────────────────────────────────────── */
  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function q(sel, ctx) { return (ctx || document).querySelector(sel); }
  function qq(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function toast(msg, type) {
    var el = q('#iq-toast');
    if (!el) return;
    el.textContent = msg;
    el.className = 'iq-toast' + (type ? ' ' + type : '');
    el.style.display = '';
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.style.display = 'none'; }, 3000);
  }

  function svgIcon(path, w, h) {
    w = w || 15; h = h || 15;
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="' + w + '" height="' + h + '">' + path + '</svg>';
  }

  var ICONS = {
    copy:     '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    check:    '<polyline points="20 6 9 17 4 12"/>',
    chevron:  '<polyline points="6 9 12 15 18 9"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    trash:    '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
    eye:      '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    load:     '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>',
  };

  /* ── State ─────────────────────────────────────────────────────────────── */
  var state = {
    questions: [],
    currentFilter: 'all',
    currentSession: null,
    savedSessionId: null,
    aiEnabled: false,
  };

  /* ── Elements ──────────────────────────────────────────────────────────── */
  var app            = q('#iq-app');
  var generateBtn    = q('#iq-generate-btn');
  var jobTitleInput  = q('#iq-job-title');
  var industrySelect = q('#iq-industry');
  var countSlider    = q('#iq-count');
  var countVal       = q('#iq-count-val');
  var contextArea    = q('#iq-context');
  var emptyEl        = q('#iq-empty');
  var loadingEl      = q('#iq-loading');
  var resultsEl      = q('#iq-results');
  var questionList   = q('#iq-question-list');
  var resultTitle    = q('#iq-results-title');
  var resultSub      = q('#iq-results-sub');
  var tabsEl         = q('#iq-tabs');
  var historyBtn     = q('#iq-history-btn');
  var drawerEl       = q('#iq-drawer');
  var drawerOverlay  = q('#iq-drawer-overlay');
  var drawerClose    = q('#iq-drawer-close');
  var drawerBody     = q('#iq-drawer-body');
  var saveBtn        = q('#iq-save-btn');
  var copyAllBtn     = q('#iq-copy-all-btn');
  var exportBtn      = q('#iq-export-btn');
  var modalOverlay   = q('#iq-modal-overlay');
  var modalClose     = q('#iq-modal-close');
  var modalCancel    = q('#iq-modal-cancel');
  var modalSave      = q('#iq-modal-save');
  var sessionNameInput = q('#iq-session-name');
  // AI settings elements
  var aiChip         = q('#iq-ai-chip');
  var settingsBtn    = q('#iq-settings-btn');
  var aiModalOverlay = q('#iq-ai-modal-overlay');
  var aiModalClose   = q('#iq-ai-modal-close');
  var aiModalCancel  = q('#iq-ai-modal-cancel');
  var aiKeySave      = q('#iq-ai-key-save');
  var aiKeyClear     = q('#iq-ai-key-clear');
  var apiKeyInput    = q('#iq-api-key-input');
  var aiStatusBox    = q('#iq-ai-status-box');
  var aiStatusDot    = q('#iq-ai-status-dot');
  var aiStatusLabel  = q('#iq-ai-status-label');
  var aiResultBadge  = q('#iq-ai-result-badge');
  var loadingTextEl  = q('.iq-loading-text');

  /* ── AI status check ───────────────────────────────────────────────────── */
  function refreshAiStatus() {
    fetch('/hrsd/interview/ai-status')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        state.aiEnabled = !!(d && d.ai_enabled);
        if (aiChip) aiChip.style.display = state.aiEnabled ? '' : 'none';
        if (aiStatusDot) aiStatusDot.className = 'iq-ai-status-dot' + (state.aiEnabled ? ' is-on' : '');
        if (aiStatusLabel) aiStatusLabel.textContent = state.aiEnabled
          ? 'Claude AI is active — questions will be role-specific and AI-generated.'
          : 'No API key configured. Using built-in question bank (less specific).';
      })
      .catch(function () {});
  }
  refreshAiStatus();

  /* ── AI Settings modal ─────────────────────────────────────────────────── */
  function openAiModal() {
    if (apiKeyInput) apiKeyInput.value = '';
    if (aiModalOverlay) aiModalOverlay.style.display = '';
    refreshAiStatus();
  }
  function closeAiModal() {
    if (aiModalOverlay) aiModalOverlay.style.display = 'none';
  }

  if (settingsBtn) settingsBtn.addEventListener('click', openAiModal);
  if (aiModalClose) aiModalClose.addEventListener('click', closeAiModal);
  if (aiModalCancel) aiModalCancel.addEventListener('click', closeAiModal);
  if (aiModalOverlay) {
    aiModalOverlay.addEventListener('click', function (e) {
      if (e.target === aiModalOverlay) closeAiModal();
    });
  }

  if (aiKeySave) {
    aiKeySave.addEventListener('click', function () {
      var key = (apiKeyInput ? apiKeyInput.value.trim() : '');
      if (!key) { toast('Please enter an API key', 'error'); return; }
      aiKeySave.disabled = true;
      fetch('/hrsd/interview/save-api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ api_key: key }),
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          aiKeySave.disabled = false;
          if (d.ok) {
            toast('API key saved! AI generation is now active.', 'success');
            closeAiModal();
            refreshAiStatus();
          } else {
            toast('Error: ' + (d.error || 'Could not save key'), 'error');
          }
        })
        .catch(function () { aiKeySave.disabled = false; toast('Network error', 'error'); });
    });
  }

  if (aiKeyClear) {
    aiKeyClear.addEventListener('click', function () {
      if (!confirm('Remove the Claude API key? AI generation will be disabled.')) return;
      fetch('/hrsd/interview/save-api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ api_key: '' }),
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.ok) { toast('API key removed.', 'success'); closeAiModal(); refreshAiStatus(); }
        })
        .catch(function () {});
    });
  }

  /* ── Slider live update ────────────────────────────────────────────────── */
  if (countSlider && countVal) {
    countSlider.addEventListener('input', function () {
      countVal.textContent = countSlider.value;
    });
  }

  /* ── Collect form values ───────────────────────────────────────────────── */
  function getConfig() {
    var levelEl = q('input[name="iq-level"]:checked');
    var types   = qq('#iq-sidebar .iq-checks input[type="checkbox"]:checked').map(function (el) { return el.value; });
    var comps   = qq('#iq-competency-grid input[type="checkbox"]:checked').map(function (el) { return el.value; });
    return {
      job_title:        (jobTitleInput ? jobTitleInput.value.trim() : ''),
      industry:         (industrySelect ? industrySelect.value : ''),
      experience_level: (levelEl ? levelEl.value : 'mid'),
      count:            parseInt(countSlider ? countSlider.value : 12, 10),
      question_types:   types,
      competencies:     comps,
      company_context:  (contextArea ? contextArea.value.trim() : ''),
    };
  }

  /* ── Show / hide panels ────────────────────────────────────────────────── */
  function showEmpty()   { emptyEl && (emptyEl.style.display = '');    loadingEl && (loadingEl.style.display = 'none'); resultsEl && (resultsEl.style.display = 'none'); }
  function showLoading() { emptyEl && (emptyEl.style.display = 'none'); loadingEl && (loadingEl.style.display = ''); resultsEl && (resultsEl.style.display = 'none'); }
  function showResults() { emptyEl && (emptyEl.style.display = 'none'); loadingEl && (loadingEl.style.display = 'none'); resultsEl && (resultsEl.style.display = ''); }

  /* ── Type label / color ────────────────────────────────────────────────── */
  var TYPE_LABELS = {
    opening:     'Opening',
    behavioral:  'Behavioral',
    technical:   'Technical',
    situational: 'Situational',
    culture_fit: 'Culture Fit',
  };

  /* ── Render a single question card ────────────────────────────────────── */
  function renderCard(q) {
    var typeLabel = TYPE_LABELS[q.type] || q.type;
    var hasFollowups = q.follow_ups && q.follow_ups.length > 0;
    var hasTips = q.tips && q.tips.length > 0;

    var followupsHtml = '';
    if (hasFollowups) {
      followupsHtml = '<div class="iq-expander">' +
        '<button type="button" class="iq-expander-toggle" data-expand="followups-' + q.id + '">' +
          'Follow-up Questions' +
          '<span class="iq-expander-icon">' + svgIcon(ICONS.chevron, 14, 14) + '</span>' +
        '</button>' +
        '<div class="iq-expander-body" id="followups-' + q.id + '">' +
          '<ul class="iq-followup-list">' +
            q.follow_ups.map(function (fu) { return '<li>' + esc(fu) + '</li>'; }).join('') +
          '</ul>' +
        '</div>' +
      '</div>';
    }

    var tipsHtml = '';
    if (hasTips) {
      tipsHtml = '<div class="iq-expander">' +
        '<button type="button" class="iq-expander-toggle" data-expand="tips-' + q.id + '">' +
          'Interviewer Tips' +
          '<span class="iq-expander-icon">' + svgIcon(ICONS.chevron, 14, 14) + '</span>' +
        '</button>' +
        '<div class="iq-expander-body" id="tips-' + q.id + '">' +
          '<div class="iq-tip-box">' + esc(q.tips) + '</div>' +
        '</div>' +
      '</div>';
    }

    return '<div class="iq-question-card" data-type="' + esc(q.type) + '" data-id="' + q.id + '">' +
      '<div class="iq-card-top">' +
        '<div class="iq-card-meta">' +
          '<div class="iq-card-num">' + q.id + '</div>' +
          '<span class="iq-type-pill ' + esc(q.type) + '">' + esc(typeLabel) + '</span>' +
          (q.competency && q.competency !== typeLabel ? '<span class="iq-comp-pill-sm">' + esc(q.competency) + '</span>' : '') +
          '<div class="iq-card-actions">' +
            '<button type="button" class="iq-icon-btn copy-q-btn" data-id="' + q.id + '" title="Copy question">' + svgIcon(ICONS.copy) + '</button>' +
          '</div>' +
        '</div>' +
        '<div class="iq-card-question">' + esc(q.text) + '</div>' +
      '</div>' +
      ((hasFollowups || hasTips) ?
        '<div class="iq-card-expanders">' + followupsHtml + tipsHtml + '</div>'
        : '') +
    '</div>';
  }

  /* ── Render all question cards ─────────────────────────────────────────── */
  function renderQuestions() {
    if (!questionList) return;
    var filtered = state.currentFilter === 'all'
      ? state.questions
      : state.questions.filter(function (q) { return q.type === state.currentFilter; });

    if (filtered.length === 0) {
      questionList.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--iq-muted);font-size:14px;">No questions in this category.</div>';
      return;
    }
    questionList.innerHTML = filtered.map(renderCard).join('');
    bindCardEvents();
  }

  /* ── Card event bindings ───────────────────────────────────────────────── */
  function bindCardEvents() {
    // Copy individual question
    qq('.copy-q-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var id = parseInt(btn.getAttribute('data-id'), 10);
        var qObj = state.questions.find(function (q) { return q.id === id; });
        if (!qObj) return;
        copyText(qObj.text);
        btn.classList.add('is-copied');
        btn.innerHTML = svgIcon(ICONS.check);
        setTimeout(function () {
          btn.classList.remove('is-copied');
          btn.innerHTML = svgIcon(ICONS.copy);
        }, 1800);
        toast('Question copied!', 'success');
      });
    });

    // Expander toggles
    qq('.iq-expander-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var targetId = btn.getAttribute('data-expand');
        var body = q('#' + targetId);
        if (!body) return;
        var open = body.classList.toggle('is-open');
        btn.classList.toggle('is-open', open);
      });
    });
  }

  /* ── Tab filter ────────────────────────────────────────────────────────── */
  if (tabsEl) {
    tabsEl.addEventListener('click', function (e) {
      var tab = e.target.closest('.iq-tab');
      if (!tab) return;
      qq('.iq-tab').forEach(function (t) { t.classList.remove('is-active'); });
      tab.classList.add('is-active');
      state.currentFilter = tab.getAttribute('data-filter') || 'all';
      renderQuestions();
    });
  }

  /* ── Generate questions ────────────────────────────────────────────────── */
  if (generateBtn) {
    generateBtn.addEventListener('click', function () {
      var cfg = getConfig();
      if (!cfg.job_title) {
        toast('Please enter a Job Title', 'error');
        jobTitleInput && jobTitleInput.focus();
        return;
      }
      if (cfg.question_types.length === 0) {
        toast('Select at least one Question Type', 'error');
        return;
      }

      showLoading();
      generateBtn.classList.add('is-loading');
      generateBtn.innerHTML = svgIcon(ICONS.load + ' class="spin"', 18, 18) + (state.aiEnabled ? ' AI Generating…' : ' Generating…');
      if (loadingTextEl) loadingTextEl.textContent = state.aiEnabled
        ? 'Generating AI-powered, role-specific questions…'
        : 'Generating questions…';

      fetch('/hrsd/interview/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify(cfg),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          generateBtn.classList.remove('is-loading');
          generateBtn.innerHTML = svgIcon('<path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/>', 18, 18) + ' Generate Questions';

          if (!data.ok) {
            toast('Error: ' + (data.error || 'Unknown error'), 'error');
            showEmpty();
            return;
          }

          state.questions = data.questions || [];
          state.currentFilter = 'all';
          state.savedSessionId = null;

          if (state.questions.length === 0) {
            toast('No questions generated. Try different settings.', 'error');
            showEmpty();
            return;
          }

          // Update header
          if (resultTitle) resultTitle.textContent = esc(cfg.job_title) + ' — Interview Guide';
          if (resultSub) {
            var lvlMap = { junior: 'Junior', mid: 'Mid-Level', senior: 'Senior', executive: 'Executive' };
            var methodBadge = '';
            if (data.generation_method === 'claude') {
              methodBadge = ' <span class="iq-method-badge ai"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="11" height="11"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg> Claude AI</span>';
            } else if (data.generation_method === 'ddg') {
              methodBadge = ' <span class="iq-method-badge web"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="11" height="11"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg> Web Search</span>';
            } else {
              methodBadge = ' <span class="iq-method-badge static">Built-in Bank</span>';
            }
            resultSub.innerHTML =
              esc(state.questions.length + ' questions · ' +
              (lvlMap[cfg.experience_level] || cfg.experience_level) +
              (cfg.industry ? ' · ' + cfg.industry : '')) + methodBadge;
          }

          // Reset active tab
          qq('.iq-tab').forEach(function (t) { t.classList.remove('is-active'); });
          var allTab = q('.iq-tab[data-filter="all"]');
          if (allTab) allTab.classList.add('is-active');

          renderQuestions();
          showResults();

          // Update save button state
          if (saveBtn) saveBtn.disabled = false;
        })
        .catch(function (err) {
          console.error(err);
          generateBtn.classList.remove('is-loading');
          generateBtn.innerHTML = svgIcon('<path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/>', 18, 18) + ' Generate Questions';
          toast('Failed to generate questions. Try again.', 'error');
          showEmpty();
        });
    });
  }

  /* ── Copy all questions ────────────────────────────────────────────────── */
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () { fallbackCopy(text); });
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;top:-999px;left:-999px';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (e) { /* ignore */ }
    document.body.removeChild(ta);
  }

  if (copyAllBtn) {
    copyAllBtn.addEventListener('click', function () {
      if (state.questions.length === 0) return;
      var cfg = getConfig();
      var lines = ['INTERVIEW GUIDE — ' + cfg.job_title.toUpperCase(), ''];
      state.questions.forEach(function (qObj) {
        lines.push('Q' + qObj.id + '. [' + (TYPE_LABELS[qObj.type] || qObj.type) + '] ' + qObj.text);
        if (qObj.follow_ups && qObj.follow_ups.length) {
          qObj.follow_ups.forEach(function (fu) { lines.push('   → ' + fu); });
        }
        lines.push('');
      });
      copyText(lines.join('\n'));
      toast('All ' + state.questions.length + ' questions copied!', 'success');
    });
  }

  /* ── Export CSV (client-side if no saved session) ───────────────────────── */
  if (exportBtn) {
    exportBtn.addEventListener('click', function () {
      if (state.savedSessionId) {
        window.location.href = '/hrsd/interview/export/' + state.savedSessionId;
        return;
      }
      // Client-side CSV
      if (state.questions.length === 0) { toast('Generate questions first.', 'error'); return; }
      var rows = [['#', 'Type', 'Competency', 'Question', 'Follow-up Questions', 'Interviewer Tips']];
      state.questions.forEach(function (qObj) {
        rows.push([
          qObj.id,
          (TYPE_LABELS[qObj.type] || qObj.type),
          qObj.competency || '',
          qObj.text,
          (qObj.follow_ups || []).join(' | '),
          qObj.tips || '',
        ]);
      });
      var csv = rows.map(function (row) {
        return row.map(function (cell) {
          var s = String(cell).replace(/"/g, '""');
          return /[",\n]/.test(s) ? '"' + s + '"' : s;
        }).join(',');
      }).join('\n');
      var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      var url  = URL.createObjectURL(blob);
      var a    = document.createElement('a');
      a.href = url; a.download = 'interview_questions.csv';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(url);
      toast('CSV exported!', 'success');
    });
  }

  /* ── Save session modal ─────────────────────────────────────────────────── */
  function openSaveModal() {
    var cfg = getConfig();
    var now = new Date();
    var dateStr = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    if (sessionNameInput) sessionNameInput.value = cfg.job_title + ' — ' + dateStr;
    if (modalOverlay) modalOverlay.style.display = '';
    setTimeout(function () { sessionNameInput && sessionNameInput.focus(); sessionNameInput && sessionNameInput.select(); }, 50);
  }

  function closeSaveModal() {
    if (modalOverlay) modalOverlay.style.display = 'none';
  }

  if (saveBtn)     saveBtn.addEventListener('click', openSaveModal);
  if (modalClose)  modalClose.addEventListener('click', closeSaveModal);
  if (modalCancel) modalCancel.addEventListener('click', closeSaveModal);
  if (modalOverlay) {
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeSaveModal();
    });
  }

  if (modalSave) {
    modalSave.addEventListener('click', function () {
      var name = sessionNameInput ? sessionNameInput.value.trim() : '';
      if (!name) { toast('Please enter a session name', 'error'); return; }
      var cfg = getConfig();
      var payload = Object.assign({}, cfg, {
        name: name,
        questions: state.questions,
      });
      modalSave.disabled = true;
      modalSave.textContent = 'Saving…';

      fetch('/hrsd/interview/session/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify(payload),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          modalSave.disabled = false;
          modalSave.innerHTML = svgIcon(ICONS.copy) + ' Save';
          if (data.ok) {
            state.savedSessionId = data.id;
            closeSaveModal();
            toast('Session "' + name + '" saved!', 'success');
          } else {
            toast('Save failed: ' + (data.error || 'Unknown'), 'error');
          }
        })
        .catch(function () {
          modalSave.disabled = false;
          modalSave.innerHTML = svgIcon(ICONS.copy) + ' Save';
          toast('Save failed. Try again.', 'error');
        });
    });
  }

  /* ── History drawer ─────────────────────────────────────────────────────── */
  var drawerOpen = false;

  function openDrawer() {
    if (!drawerEl) return;
    drawerEl.style.display = '';
    drawerOverlay && (drawerOverlay.style.display = '');
    drawerEl.setAttribute('aria-hidden', 'false');
    drawerOpen = true;
    loadHistory();
  }

  function closeDrawer() {
    if (!drawerEl) return;
    drawerEl.style.display = 'none';
    drawerOverlay && (drawerOverlay.style.display = 'none');
    drawerEl.setAttribute('aria-hidden', 'true');
    drawerOpen = false;
  }

  if (historyBtn) historyBtn.addEventListener('click', openDrawer);
  if (drawerClose) drawerClose.addEventListener('click', closeDrawer);
  if (drawerOverlay) drawerOverlay.addEventListener('click', closeDrawer);

  function loadHistory() {
    if (!drawerBody) return;
    drawerBody.innerHTML = '<div class="iq-drawer-loading">Loading sessions…</div>';

    fetch('/hrsd/interview/history')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok || !data.sessions || data.sessions.length === 0) {
          drawerBody.innerHTML = '<div class="iq-drawer-empty"><div class="iq-drawer-empty-icon">📋</div>No saved sessions yet. Generate questions and save a session to see it here.</div>';
          return;
        }
        drawerBody.innerHTML = data.sessions.map(renderSessionItem).join('');
        bindDrawerEvents();
      })
      .catch(function () {
        drawerBody.innerHTML = '<div class="iq-drawer-empty">Failed to load sessions.</div>';
      });
  }

  var LEVEL_LABELS = { junior: 'Junior', mid: 'Mid-Level', senior: 'Senior', executive: 'Executive' };

  function renderSessionItem(sess) {
    return '<div class="iq-session-item" data-sess-id="' + sess.id + '">' +
      '<div class="iq-session-header">' +
        '<div>' +
          '<div class="iq-session-title">' + esc(sess.name) + '</div>' +
          '<div class="iq-session-meta">' +
            '<span>' + esc(sess.job_title) + '</span>' +
            '<span>' + esc(LEVEL_LABELS[sess.experience_level] || sess.experience_level) + '</span>' +
            '<span>' + sess.question_count + ' questions</span>' +
            '<span>' + esc(sess.create_date) + '</span>' +
          '</div>' +
          (sess.industry ? '<div class="iq-session-badges"><span class="iq-sess-badge">' + esc(sess.industry) + '</span></div>' : '') +
        '</div>' +
        '<div class="iq-session-actions">' +
          '<button type="button" class="iq-btn iq-btn-ghost iq-btn-sm sess-view-btn" data-sess-id="' + sess.id + '" title="View">' + svgIcon(ICONS.eye) + '</button>' +
          '<a href="/hrsd/interview/export/' + sess.id + '" class="iq-btn iq-btn-ghost iq-btn-sm" title="Export CSV" download>' + svgIcon(ICONS.download) + '</a>' +
          '<button type="button" class="iq-btn iq-btn-danger iq-btn-sm sess-del-btn" data-sess-id="' + sess.id + '" title="Delete">' + svgIcon(ICONS.trash) + '</button>' +
        '</div>' +
      '</div>' +
      '<div class="iq-session-detail" id="sess-detail-' + sess.id + '"></div>' +
    '</div>';
  }

  function bindDrawerEvents() {
    // View session detail
    qq('.sess-view-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var sid = parseInt(btn.getAttribute('data-sess-id'), 10);
        var detailEl = q('#sess-detail-' + sid);
        if (!detailEl) return;
        if (detailEl.classList.contains('is-open')) {
          detailEl.classList.remove('is-open');
          return;
        }
        detailEl.innerHTML = '<div style="padding:10px 0;color:var(--iq-muted);font-size:13px;">Loading…</div>';
        detailEl.classList.add('is-open');
        fetch('/hrsd/interview/session/' + sid)
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data.ok) { detailEl.innerHTML = '<div style="color:var(--iq-red)">Failed to load.</div>'; return; }
            var qs = data.session.questions || [];
            if (qs.length === 0) { detailEl.innerHTML = '<div style="color:var(--iq-muted);font-size:13px;padding:10px 0;">No questions found.</div>'; return; }
            detailEl.innerHTML = '<div class="iq-session-qs">' +
              qs.slice(0, 5).map(function (qObj) {
                return '<div class="iq-session-q"><strong>' + qObj.id + '.</strong> ' + esc(qObj.text) + '</div>';
              }).join('') +
              (qs.length > 5 ? '<div style="font-size:12px;color:var(--iq-muted);padding:6px 0;">…and ' + (qs.length - 5) + ' more questions</div>' : '') +
              '<div style="margin-top:10px;display:flex;gap:8px;">' +
                '<button type="button" class="iq-btn iq-btn-primary iq-btn-sm sess-load-btn" data-sess-id="' + sid + '">Load into View</button>' +
              '</div>' +
            '</div>';
            bindLoadBtns();
          })
          .catch(function () { detailEl.innerHTML = '<div style="color:var(--iq-red)">Failed to load.</div>'; });
      });
    });

    // Delete session
    qq('.sess-del-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var sid = parseInt(btn.getAttribute('data-sess-id'), 10);
        if (!confirm('Delete this session?')) return;
        fetch('/hrsd/interview/session/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
          body: JSON.stringify({ id: sid }),
        })
          .then(function () { loadHistory(); toast('Session deleted.'); })
          .catch(function () { toast('Delete failed.', 'error'); });
      });
    });
  }

  function bindLoadBtns() {
    qq('.sess-load-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var sid = parseInt(btn.getAttribute('data-sess-id'), 10);
        fetch('/hrsd/interview/session/' + sid)
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data.ok) { toast('Failed to load session.', 'error'); return; }
            var sess = data.session;
            state.questions = sess.questions || [];
            state.savedSessionId = sid;
            state.currentFilter = 'all';

            if (resultTitle) resultTitle.textContent = esc(sess.job_title) + ' — Interview Guide';
            if (resultSub) {
              resultSub.textContent = state.questions.length + ' questions · ' +
                (LEVEL_LABELS[sess.experience_level] || sess.experience_level) +
                (sess.industry ? ' · ' + sess.industry : '');
            }
            qq('.iq-tab').forEach(function (t) { t.classList.remove('is-active'); });
            var allTab = q('.iq-tab[data-filter="all"]');
            if (allTab) allTab.classList.add('is-active');
            renderQuestions();
            showResults();
            closeDrawer();
            toast('Session loaded.', 'success');
          })
          .catch(function () { toast('Failed to load session.', 'error'); });
      });
    });
  }

  /* ── Enter key on job title to generate ───────────────────────────────── */
  if (jobTitleInput) {
    jobTitleInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') generateBtn && generateBtn.click();
    });
  }

  /* ── Initial state ──────────────────────────────────────────────────────── */
  showEmpty();

})();
