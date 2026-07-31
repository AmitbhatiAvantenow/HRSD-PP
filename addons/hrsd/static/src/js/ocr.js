/* =========================================================================
   AvanteNow HR Portal — OCR Document Scanner frontend
   Vanilla JS, no external deps.
   ========================================================================= */
(function () {
  'use strict';

  /* ── DOM refs ──────────────────────────────────────────────────────────── */
  var historyBtn    = document.getElementById('ocr-history-btn');
  var historyBadge  = document.getElementById('ocr-history-badge');
  var modalOverlay  = document.getElementById('ocr-modal-overlay');
  var modalClose    = document.getElementById('ocr-modal-close');
  var modalCount    = document.getElementById('ocr-modal-count');
  var dropzone      = document.getElementById('ocr-dropzone');
  var dropInner     = document.getElementById('ocr-dropzone-inner');
  var previewState  = document.getElementById('ocr-preview-state');
  var previewImg    = document.getElementById('ocr-preview-img');
  var previewPdf    = document.getElementById('ocr-preview-pdf-icon');
  var previewName   = document.getElementById('ocr-preview-filename');
  var previewSize   = document.getElementById('ocr-preview-size');
  var changeBtn     = document.getElementById('ocr-change-btn');
  var fileInput     = document.getElementById('ocr-file-input');
  var docName       = document.getElementById('ocr-doc-name');
  var docType       = document.getElementById('ocr-doc-type');
  var empSelect     = document.getElementById('ocr-employee');
  var scanBtn       = document.getElementById('ocr-scan-btn');
  var progressWrap  = document.getElementById('ocr-progress-wrap');
  var progressFill  = document.getElementById('ocr-progress-fill');
  var progressLabel = document.getElementById('ocr-progress-label');
  var emptyState    = document.getElementById('ocr-empty-state');
  var results       = document.getElementById('ocr-results');
  var textBox       = document.getElementById('ocr-text-box');
  var smartFields   = document.getElementById('ocr-smart-fields');
  var copyBtn       = document.getElementById('ocr-btn-copy');
  var downloadBtn   = document.getElementById('ocr-btn-download');
  var clearBtn      = document.getElementById('ocr-btn-clear');
  var statPages     = document.getElementById('ocr-stat-pages');
  var statWords     = document.getElementById('ocr-stat-words');
  var statConf      = document.getElementById('ocr-stat-confidence');
  var statStatus    = document.getElementById('ocr-stat-status');

  /* ── History modal ──────────────────────────────────────────────────────── */
  function openModal() { modalOverlay.classList.add('is-open'); }
  function closeModal() { modalOverlay.classList.remove('is-open'); }

  if (historyBtn) historyBtn.addEventListener('click', openModal);
  if (modalClose) modalClose.addEventListener('click', closeModal);
  if (modalOverlay) {
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeModal();
    });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  function updateHistoryCounts(delta) {
    var bottomChip = document.getElementById('ocr-history-count');
    var n = Math.max(0, (parseInt((bottomChip && bottomChip.textContent) || '0') || 0) + delta);
    if (bottomChip) bottomChip.textContent = n + ' record(s)';
    if (modalCount) modalCount.textContent = n + ' record(s)';
    if (historyBadge) historyBadge.textContent = n;
  }

  /* ── State ─────────────────────────────────────────────────────────────── */
  var currentFile   = null;
  var lastScanId    = null;
  var lastFilename  = 'extracted_text';

  /* ── CSRF token (read from Odoo session cookie or meta tag) ─────────────── */
  function getCsrf() {
    var metas = document.getElementsByTagName('meta');
    for (var i = 0; i < metas.length; i++) {
      if (metas[i].getAttribute('name') === 'csrf-token') {
        return metas[i].getAttribute('content');
      }
    }
    // Odoo stores it in the cookie 'csrf_token'
    var match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  /* ── Toast ──────────────────────────────────────────────────────────────── */
  function toast(msg, type) {
    var el = document.createElement('div');
    el.className = 'ocr-toast is-' + (type || 'success');
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { el.classList.add('is-visible'); });
    });
    setTimeout(function () {
      el.classList.remove('is-visible');
      setTimeout(function () { el.parentNode && el.parentNode.removeChild(el); }, 300);
    }, 2800);
  }

  /* ── File size formatting ────────────────────────────────────────────────── */
  function fmtSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  /* ── Show / hide drop zone ──────────────────────────────────────────────── */
  function showPreview(file) {
    currentFile = file;
    dropInner.style.display = 'none';
    previewState.style.display = 'flex';
    previewName.textContent = file.name;
    previewSize.textContent = fmtSize(file.size);
    lastFilename = file.name.replace(/\.[^.]+$/, '') || 'extracted_text';
    if (!docName.value.trim()) {
      docName.value = lastFilename;
    }

    var isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    if (isPdf) {
      previewImg.style.display = 'none';
      previewPdf.style.display = 'flex';
    } else {
      previewPdf.style.display = 'none';
      var reader = new FileReader();
      reader.onload = function (e) {
        previewImg.src = e.target.result;
        previewImg.style.display = 'block';
      };
      reader.readAsDataURL(file);
    }
    scanBtn.disabled = false;
  }

  function resetDropzone() {
    currentFile = null;
    fileInput.value = '';
    dropInner.style.display = '';
    previewState.style.display = 'none';
    previewImg.style.display = 'none';
    previewImg.src = '';
    previewPdf.style.display = 'none';
    scanBtn.disabled = true;
  }

  /* ── Drop zone interactions ─────────────────────────────────────────────── */
  dropzone.addEventListener('click', function (e) {
    if (e.target === changeBtn || changeBtn.contains(e.target)) return;
    fileInput.click();
  });

  fileInput.addEventListener('change', function () {
    if (fileInput.files && fileInput.files[0]) showPreview(fileInput.files[0]);
  });

  changeBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    resetDropzone();
    fileInput.click();
  });

  dropzone.addEventListener('dragover', function (e) {
    e.preventDefault();
    dropzone.classList.add('is-hover');
  });
  dropzone.addEventListener('dragleave', function (e) {
    if (!dropzone.contains(e.relatedTarget)) dropzone.classList.remove('is-hover');
  });
  dropzone.addEventListener('drop', function (e) {
    e.preventDefault();
    dropzone.classList.remove('is-hover');
    var file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) showPreview(file);
  });

  /* ── Progress animation ─────────────────────────────────────────────────── */
  var _progTimer = null;
  function startProgress() {
    progressWrap.style.display = '';
    progressFill.style.width = '0%';
    progressLabel.textContent = 'Uploading…';
    var pct = 0;
    _progTimer = setInterval(function () {
      if (pct < 40)       { pct += 8;  progressLabel.textContent = 'Uploading…'; }
      else if (pct < 75)  { pct += 4;  progressLabel.textContent = 'Running OCR…'; }
      else if (pct < 92)  { pct += 1;  progressLabel.textContent = 'Extracting fields…'; }
      progressFill.style.width = pct + '%';
    }, 200);
  }
  function endProgress(success) {
    clearInterval(_progTimer);
    progressFill.style.width = '100%';
    progressLabel.textContent = success ? 'Done!' : 'Finished with errors.';
    setTimeout(function () { progressWrap.style.display = 'none'; }, 1200);
  }

  /* ── Smart fields renderer ──────────────────────────────────────────────── */
  var FIELD_META = {
    employee_name:    { emoji: '👤', label: 'Employee Name' },
    employee_id_code: { emoji: '🪪', label: 'Employee ID' },
    designation:      { emoji: '💼', label: 'Designation' },
    department:       { emoji: '🏢', label: 'Department' },
    salary:           { emoji: '💰', label: 'Salary' },
    emails:           { emoji: '📧', label: 'Email(s)' },
    phones:           { emoji: '📞', label: 'Phone(s)' },
    dates:            { emoji: '📅', label: 'Dates' },
    amounts:          { emoji: '💸', label: 'Amounts' },
    emirates_ids:     { emoji: '🪪', label: 'Emirates ID' },
    passport_numbers: { emoji: '📘', label: 'Passport No.' },
  };

  function renderSmartFields(fields) {
    var html = '';
    var count = 0;
    Object.keys(FIELD_META).forEach(function (key) {
      var val = fields[key];
      if (!val) return;
      var vals = Array.isArray(val) ? val : [val];
      if (!vals.length) return;
      count++;
      var meta = FIELD_META[key];
      html += '<div class="ocr-smart-card">' +
        '<div class="ocr-smart-card-header">' +
        '<span class="ocr-smart-card-emoji">' + meta.emoji + '</span>' +
        meta.label +
        '</div>' +
        '<div class="ocr-smart-values">' +
        vals.map(function (v) {
          return '<div class="ocr-smart-value" title="' + v + '">' + v + '</div>';
        }).join('') +
        '</div></div>';
    });

    var emptyEl = document.getElementById('ocr-smart-empty');
    if (count === 0) {
      if (emptyEl) emptyEl.style.display = '';
    } else {
      if (emptyEl) emptyEl.style.display = 'none';
      smartFields.insertAdjacentHTML('afterbegin', html);
    }
  }

  function clearSmartFields() {
    var cards = smartFields.querySelectorAll('.ocr-smart-card');
    cards.forEach(function (c) { c.parentNode.removeChild(c); });
    var emptyEl = document.getElementById('ocr-smart-empty');
    if (emptyEl) emptyEl.style.display = '';
  }

  /* ── Show results ────────────────────────────────────────────────────────── */
  var empStatEl     = document.getElementById('ocr-stat-employee');
  var empNameEl     = document.getElementById('ocr-stat-emp-name');
  var attachBadgeEl = document.getElementById('ocr-attach-badge');

  function showResults(data) {
    emptyState.style.display = 'none';
    results.style.display = '';

    statPages.textContent = (data.page_count || 1) + ' page' + (data.page_count !== 1 ? 's' : '');
    statWords.textContent = (data.word_count || 0) + ' words';
    statConf.textContent  = (data.confidence || 0).toFixed(1) + '% confidence';

    // Employee attachment pill
    if (data.employee_name && data.employee_url) {
      empNameEl.textContent = data.employee_name;
      empStatEl.href = data.employee_url;
      empStatEl.style.display = '';
      if (data.attachment_id) {
        attachBadgeEl.style.display = '';
        empStatEl.title = 'Document saved to employee attachments — click to open employee';
      } else {
        attachBadgeEl.style.display = 'none';
      }
    } else {
      empStatEl.style.display = 'none';
    }

    if (data.error) {
      statStatus.className = 'ocr-stat-chip';
      statStatus.style.background = '#fee2e2';
      statStatus.style.borderColor = '#fca5a5';
      statStatus.style.color = '#991b1b';
      statStatus.innerHTML = '<span class="ocr-stat-icon">⚠️</span> <span>Error</span>';
      textBox.value = '';
      var errDiv = document.createElement('div');
      errDiv.className = 'ocr-error-banner';
      errDiv.textContent = data.error;
      textBox.parentNode.insertBefore(errDiv, textBox);
    } else {
      statStatus.className = 'ocr-stat-chip ocr-stat-success';
      statStatus.style.cssText = '';
      statStatus.innerHTML = '<span class="ocr-stat-icon">✅</span> <span>Scanned</span>';
      textBox.value = data.text || '';
    }

    clearSmartFields();
    renderSmartFields(data.smart_fields || {});
    lastScanId = data.scan_id || null;
    if (data.scan_id && currentFile) {
      lastFilename = currentFile.name.replace(/\.[^.]+$/, '');
    }
  }

  /* ── Scan submit ─────────────────────────────────────────────────────────── */
  scanBtn.addEventListener('click', function () {
    if (!currentFile) { toast('Please select a file first.', 'error'); return; }

    var fd = new FormData();
    fd.append('file', currentFile);
    fd.append('doc_name', docName.value.trim());
    fd.append('doc_type', docType.value);
    fd.append('employee_id', empSelect.value || '');
    fd.append('csrf_token', getCsrf());

    scanBtn.disabled = true;
    startProgress();

    fetch('/hrsd/ocr/scan', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        endProgress(!data.error);
        if (!data.success && !data.text) {
          toast('Scan failed: ' + (data.error || 'Unknown error'), 'error');
        } else {
          showResults(data);
          appendHistoryRow(data);
          if (!data.error) toast('Document scanned successfully!', 'success');
        }
      })
      .catch(function (err) {
        endProgress(false);
        toast('Request failed: ' + err.message, 'error');
      })
      .finally(function () {
        scanBtn.disabled = false;
      });
  });

  /* ── History row append ──────────────────────────────────────────────────── */
  function buildRowHTML(data, name, type, empCell, attachCell, conf, dateStr) {
    return '<td class="ocr-td-name"><button class="ocr-load-btn" data-id="' + data.scan_id + '">' + name + '</button></td>' +
      '<td><span class="ocr-type-tag">' + type + '</span></td>' +
      '<td>' + empCell + '</td>' +
      '<td>' + attachCell + '</td>' +
      '<td>' + (data.page_count || 1) + '</td>' +
      '<td>' + (data.word_count || 0) + '</td>' +
      '<td><div class="ocr-conf-bar"><div><div class="ocr-conf-fill" style="width:' + conf + '%"></div></div><span>' + conf + '%</span></div></td>' +
      '<td class="ocr-td-date">' + dateStr + '</td>' +
      '<td>You</td>' +
      '<td><span class="ocr-state-badge is-' + (data.error ? 'error' : 'done') + '">' + (data.error ? 'Error' : 'Scanned') + '</span></td>' +
      '<td><button class="ocr-del-btn" data-id="' + data.scan_id + '" title="Delete">✕</button></td>';
  }

  function appendHistoryRow(data) {
    if (!data.scan_id) return;
    var name = (docName.value.trim() || currentFile && currentFile.name.replace(/\.[^.]+$/, '') || 'Document');
    var type = docType.options[docType.selectedIndex].text;
    var emp  = empSelect.options[empSelect.selectedIndex].text;
    if (emp === '— No employee —') emp = '—';
    var now  = new Date();
    var dateStr = now.getDate().toString().padStart(2, '0') + ' ' +
      ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][now.getMonth()] +
      ' ' + now.getFullYear() + ' ' +
      now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');

    var conf = (data.confidence || 0).toFixed(0);
    var empCell = data.employee_url
      ? '<a href="' + data.employee_url + '" class="ocr-emp-link" target="_self">' + (data.employee_name || emp) + '</a>'
      : (emp === '— No employee —' ? '—' : emp);
    var attachCell = data.attachment_id
      ? '<a href="/odoo/employees/' + (empSelect.value || '') + '" class="ocr-attach-link" target="_self" title="Saved to employee attachments">📎 Saved</a>'
      : '<span class="ocr-no-attach">—</span>';

    var html = buildRowHTML(data, name, type, empCell, attachCell, conf, dateStr);

    // Add to bottom history table
    var tbody = document.querySelector('.ocr-history-section .ocr-history-table tbody');
    if (tbody) {
      var tr = document.createElement('tr');
      tr.className = 'ocr-history-row';
      tr.setAttribute('data-id', data.scan_id);
      tr.innerHTML = html;
      tbody.insertBefore(tr, tbody.firstChild);
      wireHistoryRow(tr);
    }

    // Add to modal table
    var modalTbody = document.getElementById('ocr-modal-tbody');
    if (modalTbody) {
      var mtr = document.createElement('tr');
      mtr.className = 'ocr-history-row';
      mtr.setAttribute('data-id', data.scan_id);
      mtr.innerHTML = html;
      modalTbody.insertBefore(mtr, modalTbody.firstChild);
      wireHistoryRow(mtr);
      var emptyEl = document.getElementById('ocr-modal-empty');
      if (emptyEl) emptyEl.style.display = 'none';
    }

    updateHistoryCounts(+1);
  }

  /* ── Load scan from history ──────────────────────────────────────────────── */
  function wireHistoryRow(row) {
    var loadBtn = row.querySelector('.ocr-load-btn');
    var delBtn  = row.querySelector('.ocr-del-btn');

    if (loadBtn) {
      loadBtn.addEventListener('click', function () {
        var id = loadBtn.getAttribute('data-id');
        fetch('/hrsd/ocr/load/' + id, { credentials: 'same-origin' })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.success) {
              showResults({
                text: data.text,
                smart_fields: data.smart_fields,
                page_count: data.page_count,
                word_count: data.word_count,
                confidence: data.confidence,
                error: data.state === 'error' ? (data.error || 'Scan error') : null,
                scan_id: data.scan_id,
                employee_name: data.employee_name || '',
                employee_url: data.employee_url || '',
                attachment_id: data.attachment_id || null,
              });
              lastFilename = data.name || 'document';
              closeModal();
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }
          })
          .catch(function () { toast('Could not load scan.', 'error'); });
      });
    }

    if (delBtn) {
      delBtn.addEventListener('click', function () {
        var id = delBtn.getAttribute('data-id');
        if (!confirm('Delete this scan record?')) return;
        var fd = new FormData();
        fd.append('csrf_token', getCsrf());
        fetch('/hrsd/ocr/delete/' + id, { method: 'POST', body: fd, credentials: 'same-origin' })
          .then(function (r) { return r.json(); })
          .then(function () {
            // remove from all tables (bottom + modal)
            document.querySelectorAll('tr[data-id="' + id + '"]').forEach(function (rowEl) {
              rowEl.parentNode.removeChild(rowEl);
            });
            updateHistoryCounts(-1);
            if (lastScanId == id) {
              emptyState.style.display = '';
              results.style.display = 'none';
            }
            toast('Scan deleted.', 'success');
          })
          .catch(function () { toast('Delete failed.', 'error'); });
      });
    }
  }

  // Wire existing history rows on page load (bottom table + modal)
  document.querySelectorAll('.ocr-history-row').forEach(wireHistoryRow);

  /* ── Copy ────────────────────────────────────────────────────────────────── */
  if (copyBtn) {
    copyBtn.addEventListener('click', function () {
      var text = textBox.value;
      if (!text) { toast('Nothing to copy.', 'error'); return; }
      navigator.clipboard.writeText(text).then(function () {
        copyBtn.classList.add('is-copied');
        setTimeout(function () { copyBtn.classList.remove('is-copied'); }, 2000);
        toast('Copied to clipboard!', 'success');
      }).catch(function () {
        textBox.select();
        document.execCommand('copy');
        toast('Copied!', 'success');
      });
    });
  }

  /* ── Download ────────────────────────────────────────────────────────────── */
  if (downloadBtn) {
    downloadBtn.addEventListener('click', function () {
      var text = textBox.value;
      if (!text) { toast('Nothing to download.', 'error'); return; }
      var blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      var url  = URL.createObjectURL(blob);
      var a    = document.createElement('a');
      a.href = url;
      a.download = (lastFilename || 'extracted_text') + '_ocr.txt';
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  /* ── Clear ───────────────────────────────────────────────────────────────── */
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      results.style.display = 'none';
      emptyState.style.display = '';
      clearSmartFields();
      textBox.value = '';
      var errBanner = document.querySelector('.ocr-error-banner');
      if (errBanner) errBanner.parentNode.removeChild(errBanner);
      lastScanId = null;
    });
  }

})();
