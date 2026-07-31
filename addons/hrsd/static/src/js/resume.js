/* AI Resume Screening — resume.js */
'use strict';

(function () {
  /* ── Helpers ─────────────────────────────── */
  function getCsrf() {
    const m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.content : '';
  }

  function toast(msg, type) {
    const t = document.createElement('div');
    t.className = 'rs-toast ' + (type || '');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  }

  async function post(url, body) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const text = await r.text();
    try {
      return JSON.parse(text);
    } catch (_) {
      return { ok: false, error: `Server error ${r.status}` };
    }
  }

  /* ── Job selector ────────────────────────── */
  const jobSelect = document.getElementById('rs-job-select');
  if (jobSelect) {
    jobSelect.addEventListener('change', function () {
      const id = this.value;
      window.location.href = '/hrsd/resume?job_id=' + id;
    });
  }

  /* ── New job button ──────────────────────── */
  const newJobBtn = document.getElementById('rs-new-job-btn');
  if (newJobBtn) {
    newJobBtn.addEventListener('click', function () {
      window.location.href = '/hrsd/resume?job_id=new';
    });
  }

  /* ── Job form save ───────────────────────── */
  const jobForm = document.getElementById('rs-job-form');
  if (jobForm) {
    jobForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const jobId    = document.getElementById('rs-job-id').value;
      const title    = document.getElementById('rs-job-title').value.trim();
      const reqSk    = document.getElementById('rs-req-skills').value.trim();
      const prefSk   = document.getElementById('rs-pref-skills').value.trim();
      const minExp   = parseInt(document.getElementById('rs-min-exp').value) || 0;
      const eduLevel = document.getElementById('rs-edu-level').value;
      const jd       = document.getElementById('rs-jd').value.trim();

      if (!title) { toast('Job title is required.', 'error'); return; }

      const saveBtn = jobForm.querySelector('.rs-save-btn');
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving…';

      try {
        const res = await post('/hrsd/resume/job/save', {
          id: jobId === '0' ? null : parseInt(jobId),
          name:             title,
          required_skills:  reqSk,
          preferred_skills: prefSk,
          min_experience:   minExp,
          education_level:  eduLevel,
          job_description:  jd,
        });
        if (res.ok) {
          toast('Job profile saved!', 'success');
          window.location.href = '/hrsd/resume?job_id=' + res.id;
        } else {
          toast('Save failed: ' + (res.error || 'unknown error'), 'error');
        }
      } catch (err) {
        toast('Network error.', 'error');
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 Save Profile';
      }
    });
  }

  /* ── Drop-zone & file upload ─────────────── */
  const dropzone   = document.getElementById('rs-dropzone');
  const fileInput  = document.getElementById('rs-file-input');
  const upProgress = document.getElementById('rs-upload-progress');
  const progressFill = document.getElementById('rs-progress-fill');
  const progressLabel = document.getElementById('rs-progress-label');

  if (dropzone) {
    dropzone.addEventListener('click', () => fileInput && fileInput.click());

    ['dragenter', 'dragover'].forEach(evt =>
      dropzone.addEventListener(evt, e => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
      })
    );
    ['dragleave', 'drop'].forEach(evt =>
      dropzone.addEventListener(evt, e => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
      })
    );
    dropzone.addEventListener('drop', e => {
      const files = e.dataTransfer.files;
      if (files.length) uploadFiles(files);
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', function () {
      if (this.files.length) uploadFiles(this.files);
    });
  }

  function getJobId() {
    const el = document.getElementById('rs-job-id');
    return el ? (parseInt(el.value) || 0) : 0;
  }

  function setProgress(pct, label) {
    if (progressFill)  progressFill.style.width = pct + '%';
    if (progressLabel) progressLabel.textContent = label;
  }

  async function uploadFiles(files) {
    const jobId = getJobId();
    if (!jobId) {
      toast('Save a job profile first before uploading resumes.', 'error');
      return;
    }

    const allowed = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     'application/msword', 'text/plain'];
    const valid   = Array.from(files).filter(f =>
      allowed.includes(f.type) || /\.(pdf|docx|doc|txt)$/i.test(f.name)
    );

    if (!valid.length) {
      toast('Only PDF, DOCX, DOC, or TXT files are accepted.', 'error');
      return;
    }

    upProgress && (upProgress.style.display = 'flex');
    dropzone   && (dropzone.style.pointerEvents = 'none');

    let done = 0;
    for (const file of valid) {
      setProgress(Math.round(done / valid.length * 100),
                  `Processing ${file.name} (${done + 1}/${valid.length})…`);

      try {
        const b64 = await readBase64(file);
        const res = await post('/hrsd/resume/upload', {
          job_id:    jobId,
          file_name: file.name,
          file_data: b64,
          file_size_kb: Math.round(file.size / 1024),
        });

        if (res.ok) {
          appendCandidateCard(res.candidate);
          updateCountChip(1);
          toast(`✓ ${res.candidate.name}`, 'success');
        } else {
          toast(`${file.name}: ${res.error || 'Parse error'}`, 'error');
        }
      } catch (err) {
        toast(`${file.name}: upload failed`, 'error');
      }
      done++;
    }

    setProgress(100, 'Done!');
    setTimeout(() => {
      upProgress && (upProgress.style.display = 'none');
      dropzone   && (dropzone.style.pointerEvents = '');
    }, 1200);

    hideEmpty();
    if (fileInput) fileInput.value = '';
  }

  function readBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload  = e => resolve(e.target.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  /* ── Update count chip ───────────────────── */
  function updateCountChip(delta) {
    const chip = document.getElementById('rs-count-chip');
    if (!chip) return;
    const m = chip.textContent.match(/\d+/);
    const n = m ? parseInt(m[0]) + delta : delta;
    chip.textContent = n + ' candidate(s)';
  }

  function hideEmpty() {
    const el = document.getElementById('rs-empty');
    if (el) el.style.display = 'none';
  }

  /* ── Append candidate card ───────────────── */
  function appendCandidateCard(c) {
    const container = document.getElementById('rs-candidates');
    if (!container) return;

    const ringClass = c.score_overall >= 75 ? 'green' : c.score_overall >= 50 ? 'amber' : 'red';
    const topRank   = c.rank && c.rank <= 3 ? ` top-${c.rank}` : '';

    const matchedChips = (c.matched_skills || []).map(s =>
      `<span class="rs-skill-chip matched">✓ ${s}</span>`).join('');
    const missingChips = (c.missing_skills || []).slice(0, 4).map(s =>
      `<span class="rs-skill-chip missing">✗ ${s}</span>`).join('');
    const neutralSkills = (c.detected_skills || [])
      .filter(s => !(c.matched_skills || []).includes(s) && !(c.missing_skills || []).includes(s))
      .slice(0, 4)
      .map(s => `<span class="rs-skill-chip neutral">${s}</span>`).join('');

    const div = document.createElement('div');
    div.className = 'rs-card';
    div.dataset.id    = c.id;
    div.dataset.state = c.state;
    div.innerHTML = `
      <div class="rs-card-header">
        <div class="rs-rank-badge${topRank}">#${c.rank || '—'}</div>
        <div class="rs-card-info">
          <div class="rs-card-name">${esc(c.name)}</div>
          <div class="rs-card-meta">
            ${c.email         ? `<span>✉ ${esc(c.email)}</span>` : ''}
            ${c.phone         ? `<span>📞 ${esc(c.phone)}</span>` : ''}
            ${c.experience_years ? `<span>⏱ ${c.experience_years.toFixed(1)} yrs exp</span>` : ''}
            ${c.education_level  ? `<span>🎓 ${esc(c.education_level)}</span>` : ''}
          </div>
        </div>
        <div class="rs-card-right">
          <div class="rs-score-ring ${ringClass}">
            ${Math.round(c.score_overall)}<span class="rs-score-pct">%</span>
          </div>
          <span class="rs-status-badge is-${c.state}">${esc(c.state_label)}</span>
        </div>
      </div>
      <div class="rs-score-bars">
        ${bar('Skills', 'indigo', c.score_skills)}
        ${bar('Exp',    'green',  c.score_experience)}
        ${bar('Edu',    'amber',  c.score_education)}
        ${bar('Match',  'purple', c.score_content)}
      </div>
      <div class="rs-skills-row">${matchedChips}${missingChips}${neutralSkills}</div>
      <div class="rs-card-actions">
        <button type="button" class="rs-act shortlist" data-id="${c.id}">✅ Shortlist</button>
        <button type="button" class="rs-act reject"    data-id="${c.id}">❌ Reject</button>
        <button type="button" class="rs-act expand"    data-id="${c.id}">🔍 Details</button>
        <button type="button" class="rs-act del"       data-id="${c.id}">🗑</button>
      </div>`;
    container.prepend(div);
    wireCard(div, c);
  }

  function bar(label, color, val) {
    const w = Math.min(100, val || 0).toFixed(0);
    return `<div class="rs-bar-row">
      <span class="rs-bar-label">${label}</span>
      <div class="rs-bar-track"><div class="rs-bar-fill ${color}" style="width:${w}%"/></div>
      <span class="rs-bar-val">${w}%</span>
    </div>`;
  }

  function esc(s) {
    if (!s) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ── Wire existing cards on load ─────────── */
  document.querySelectorAll('.rs-card').forEach(card => wireCard(card));

  function wireCard(card, candidateData) {
    const id = card.dataset.id;

    card.querySelector('.rs-act.shortlist')?.addEventListener('click', () =>
      updateStatus(id, 'shortlisted', card));
    card.querySelector('.rs-act.reject')?.addEventListener('click', () =>
      updateStatus(id, 'rejected', card));
    card.querySelector('.rs-act.expand')?.addEventListener('click', () =>
      openModal(id, card));
    card.querySelector('.rs-act.del')?.addEventListener('click', () =>
      deleteCandidate(id, card));
  }

  /* ── Update candidate status ─────────────── */
  async function updateStatus(id, status, card) {
    try {
      const res = await post('/hrsd/resume/candidate/status', { id: parseInt(id), status });
      if (res.ok) {
        card.dataset.state = status;
        const badge = card.querySelector('.rs-status-badge');
        if (badge) {
          badge.className = `rs-status-badge is-${status}`;
          badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }
        if (status === 'rejected') card.style.opacity = '.7';
        else card.style.opacity = '';
        toast(status === 'shortlisted' ? '✅ Shortlisted!' : '❌ Rejected', status === 'shortlisted' ? 'success' : 'error');
      } else {
        toast('Update failed.', 'error');
      }
    } catch {
      toast('Network error.', 'error');
    }
  }

  /* ── Delete candidate ────────────────────── */
  async function deleteCandidate(id, card) {
    if (!confirm('Delete this candidate? This cannot be undone.')) return;
    try {
      const res = await post('/hrsd/resume/candidate/delete', { id: parseInt(id) });
      if (res.ok) {
        card.remove();
        updateCountChip(-1);
        toast('Candidate deleted.', 'success');
      } else {
        toast('Delete failed.', 'error');
      }
    } catch {
      toast('Network error.', 'error');
    }
  }

  /* ── Detail modal ────────────────────────── */
  const modal      = document.getElementById('rs-modal');
  const modalTitle = document.getElementById('rs-modal-title');
  const modalText  = document.getElementById('rs-modal-text');
  const modalClose = document.getElementById('rs-modal-close');

  if (modalClose) {
    modalClose.addEventListener('click', () => { if (modal) modal.style.display = 'none'; });
  }
  if (modal) {
    modal.addEventListener('click', e => {
      if (e.target === modal) modal.style.display = 'none';
    });
  }

  async function openModal(id, card) {
    const name = card.querySelector('.rs-card-name')?.textContent || 'Candidate';
    if (modalTitle) modalTitle.textContent = name + ' — Resume Text';
    if (modalText)  modalText.value = 'Loading…';
    if (modal) modal.style.display = 'flex';

    try {
      const res = await fetch('/hrsd/resume/candidate/detail?id=' + id);
      const data = await res.json();
      if (modalText) modalText.value = data.raw_text || '(No text extracted)';
    } catch {
      if (modalText) modalText.value = 'Failed to load.';
    }
  }

  /* ── Re-rank button ──────────────────────── */
  const rerankBtn = document.getElementById('rs-rerank-btn');
  if (rerankBtn) {
    rerankBtn.addEventListener('click', async function () {
      const jobId = getJobId();
      if (!jobId) { toast('No job profile selected.', 'error'); return; }
      rerankBtn.disabled = true;
      rerankBtn.textContent = '⏳ Re-ranking…';
      try {
        const res = await post('/hrsd/resume/rerank', { job_id: jobId });
        if (res.ok) {
          toast('Re-ranked! Refreshing…', 'success');
          setTimeout(() => window.location.reload(), 800);
        } else {
          toast('Re-rank failed: ' + (res.error || ''), 'error');
        }
      } catch {
        toast('Network error.', 'error');
      } finally {
        rerankBtn.disabled = false;
        rerankBtn.textContent = '🔄 Re-Rank';
      }
    });
  }

  /* ── Status filter ───────────────────────── */
  const filterStatus = document.getElementById('rs-filter-status');
  if (filterStatus) {
    filterStatus.addEventListener('change', function () {
      const val = this.value;
      document.querySelectorAll('.rs-card').forEach(card => {
        card.style.display = (!val || card.dataset.state === val) ? '' : 'none';
      });
    });
  }

  /* ── History modal ───────────────────────── */
  const histBtn      = document.getElementById('rs-history-btn');
  const histBackdrop = document.getElementById('rs-hist-backdrop');
  const histClose    = document.getElementById('rs-hist-close');
  const histLoading  = document.getElementById('rs-hist-loading');
  const histEmpty    = document.getElementById('rs-hist-empty');
  const histList     = document.getElementById('rs-hist-list');
  const histCount    = document.getElementById('rs-hist-footer-count');
  const histSubLabel = document.getElementById('rs-hist-count-label');
  const histSearch   = document.getElementById('rs-hist-search');
  const histJobSel   = document.getElementById('rs-hist-job');
  const histStSel    = document.getElementById('rs-hist-status');
  const histExport   = document.getElementById('rs-hist-export');

  let histAllRows = [];
  let histLoaded  = false;

  function histScoreClass(v) { return v >= 75 ? 'green' : v >= 50 ? 'amber' : 'red'; }

  function histRankClass(r) {
    if (r === 1) return 'top-1';
    if (r === 2) return 'top-2';
    if (r === 3) return 'top-3';
    return '';
  }

  function renderHistRows(rows) {
    // remove existing rows (keep loading/empty nodes)
    histList.querySelectorAll('.rs-hist-row').forEach(el => el.remove());
    histEmpty.style.display = 'none';

    if (!rows.length) {
      histEmpty.style.display = '';
      histCount.textContent = '0 records';
      histSubLabel.textContent = 'No candidates match your filter';
      return;
    }
    histCount.textContent = rows.length + ' record(s)';
    histSubLabel.textContent = rows.length + ' candidate(s) found';

    rows.forEach(c => {
      const div = document.createElement('div');
      div.className = 'rs-hist-row';
      div.innerHTML = `
        <div class="rs-hist-rank-dot ${histRankClass(c.rank)}">#${c.rank || '—'}</div>
        <div class="rs-hist-info">
          <div class="rs-hist-cname">${esc(c.name)}</div>
          <div class="rs-hist-cmeta">
            ${c.email ? `<span>✉ ${esc(c.email)}</span>` : ''}
            ${c.phone ? `<span>📞 ${esc(c.phone)}</span>` : ''}
            ${c.experience_years ? `<span>⏱ ${c.experience_years.toFixed(1)} yrs</span>` : ''}
            ${c.education_level ? `<span>🎓 ${esc(c.education_level)}</span>` : ''}
            <span>📅 ${esc(c.create_date)}</span>
          </div>
        </div>
        <span class="rs-hist-job-tag" title="${esc(c.job_name)}">${esc(c.job_name)}</span>
        <div class="rs-hist-score-ring ${histScoreClass(c.score_overall)}">${c.score_overall.toFixed(0)}%</div>
        <div class="rs-hist-right">
          <span class="rs-status-badge is-${c.state}">${esc(c.state_label)}</span>
          <span class="rs-hist-arrow">›</span>
        </div>`;
      div.addEventListener('click', () => {
        window.location.href = '/hrsd/resume?job_id=' + c.job_id;
      });
      histList.appendChild(div);
    });
  }

  function histFilter() {
    const q  = histSearch ? histSearch.value.toLowerCase() : '';
    const jb = histJobSel ? histJobSel.value : '';
    const st = histStSel  ? histStSel.value  : '';
    const out = histAllRows.filter(c => {
      if (q  && !c.name.toLowerCase().includes(q) && !c.email.toLowerCase().includes(q)) return false;
      if (jb && String(c.job_id) !== jb) return false;
      if (st && c.state !== st) return false;
      return true;
    });
    renderHistRows(out);
  }

  async function loadHist() {
    if (histLoaded) { histFilter(); return; }
    histLoading.style.display = '';
    histEmpty.style.display   = 'none';
    histList.querySelectorAll('.rs-hist-row').forEach(el => el.remove());
    try {
      const r    = await fetch('/hrsd/resume/history');
      const data = await r.json();
      if (!data.ok) { histLoading.querySelector('span').textContent = 'Failed to load.'; return; }

      histAllRows = data.candidates;
      histLoaded  = true;

      const jobs = {};
      histAllRows.forEach(c => { if (c.job_id) jobs[c.job_id] = c.job_name; });
      if (histJobSel) {
        histJobSel.innerHTML = '<option value="">All Jobs</option>';
        Object.entries(jobs).forEach(([id, name]) => {
          const o = document.createElement('option');
          o.value = id; o.textContent = name;
          histJobSel.appendChild(o);
        });
      }
      histLoading.style.display = 'none';
      if (histAllRows.length && histExport) histExport.style.display = '';
      histFilter();
    } catch (_) {
      histLoading.querySelector('span').textContent = 'Error loading history.';
    }
  }

  function histExportCSV() {
    const q  = histSearch ? histSearch.value.toLowerCase() : '';
    const jb = histJobSel ? histJobSel.value : '';
    const st = histStSel  ? histStSel.value  : '';
    const rows = histAllRows.filter(c => {
      if (q  && !c.name.toLowerCase().includes(q) && !c.email.toLowerCase().includes(q)) return false;
      if (jb && String(c.job_id) !== jb) return false;
      if (st && c.state !== st) return false;
      return true;
    });
    const hdr = ['Rank','Name','Email','Phone','Job','Overall%','Skills%','Exp%','Edu%','Content%','Exp(yrs)','Education','Status','Uploaded','By'];
    const lines = [hdr.join(',')];
    rows.forEach(c => lines.push([
      c.rank, `"${c.name}"`, `"${c.email}"`, `"${c.phone}"`, `"${c.job_name}"`,
      c.score_overall, c.score_skills, c.score_experience, c.score_education, c.score_content,
      c.experience_years, `"${c.education_level}"`, c.state, `"${c.create_date}"`, `"${c.uploaded_by}"`
    ].join(',')));
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' }));
    a.download = 'resume_history.csv';
    a.click();
  }

  function openHist()  { histBackdrop.style.display = ''; loadHist(); }
  function closeHist() { histBackdrop.style.display = 'none'; }

  if (histBtn)      histBtn.addEventListener('click', openHist);
  if (histClose)    histClose.addEventListener('click', closeHist);
  if (histBackdrop) histBackdrop.addEventListener('click', e => { if (e.target === histBackdrop) closeHist(); });
  if (histExport)   histExport.addEventListener('click', e => { e.preventDefault(); histExportCSV(); });
  [histSearch, histJobSel, histStSel].forEach(el => {
    if (el) { el.addEventListener('input', histFilter); el.addEventListener('change', histFilter); }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && histBackdrop && histBackdrop.style.display !== 'none') closeHist(); });
})();
