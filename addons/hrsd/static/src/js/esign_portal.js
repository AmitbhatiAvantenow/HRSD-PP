/* =========================================================================
   HR Sign — Secure Signing Portal (draw / type / upload signature capture,
   plus live drag-and-drop field filling for text/date/checkbox/etc. fields
   placed on the document via the "Place Fields" wizard step)
   ========================================================================= */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  function getCsrf() {
    var metas = document.getElementsByTagName("meta");
    for (var i = 0; i < metas.length; i++) {
      if (metas[i].getAttribute("name") === "csrf-token") return metas[i].getAttribute("content");
    }
    var match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function postForm(url, data) {
    var fd = new FormData();
    fd.append("csrf_token", getCsrf());
    Object.keys(data).forEach(function (k) { fd.append(k, data[k]); });
    return fetch(url, { method: "POST", body: fd }).then(function (r) { return r.json(); });
  }

  var FIELD_LABELS = {
    name: "Name", email: "Email", phone: "Phone", company: "Company",
    text: "Text", multiline: "Text", selection: "Selection", date: "Date",
  };

  document.addEventListener("DOMContentLoaded", function () {
    var pageData = JSON.parse(($("esp-page-data") || {}).textContent || "{}");
    var alreadySigned = pageData.signer_status === "signed";

    // Maps field id -> { type: "checkbox"|"value", el } for every fillable
    // (non-signature) field placed for this signer, gathered on submit.
    var fieldInputs = {};
    // Every "Sign here" / "Initial here" box currently on the page, so we
    // can drop a live preview of the captured signature into all of them
    // the moment the signer draws/types/uploads it — otherwise the only
    // feedback lives in the side panel and the boxes look inert.
    var signBoxes = [];

    /* ================================================================
       Document preview — PDF pages rendered via pdf.js, with an
       interactive overlay for this signer's own fillable fields.
       ================================================================ */
    function buildFieldOverlay(pageWrap, fields) {
      fields.forEach(function (f) {
        var box = document.createElement("div");
        box.className = "esp-field-box esp-field-" + f.field_type;
        box.style.left = f.pos_x + "%";
        box.style.top = f.pos_y + "%";
        box.style.width = f.width + "%";
        box.style.height = f.height + "%";

        if (f.field_type === "signature" || f.field_type === "initial") {
          box.classList.add("esp-field-sign");
          var signLabel = document.createElement("span");
          signLabel.className = "esp-field-sign-label";
          signLabel.textContent = f.field_type === "initial" ? "Initial here" : "Sign here";
          box.appendChild(signLabel);
          box.addEventListener("click", function () {
            var card = $("esp-sign-card");
            card.scrollIntoView({ behavior: "smooth", block: "center" });
            card.classList.add("esp-highlight");
            setTimeout(function () { card.classList.remove("esp-highlight"); }, 900);
          });
          signBoxes.push(box);
        } else if (f.field_type === "checkbox" || f.field_type === "radio" || f.field_type === "stamp") {
          var cb = document.createElement("input");
          cb.type = "checkbox";
          cb.className = f.field_type === "stamp" ? "esp-field-checkbox esp-field-stamp-check" : "esp-field-checkbox";
          cb.checked = f.value === "1";
          box.appendChild(cb);
          if (f.field_type === "stamp") {
            var stampLabel = document.createElement("span");
            stampLabel.className = "esp-field-stamp-label";
            stampLabel.textContent = "Stamp";
            box.appendChild(stampLabel);
          }
          fieldInputs[f.id] = { type: "checkbox", required: !!f.required, el: cb };
        } else if (f.field_type === "multiline") {
          var ta = document.createElement("textarea");
          ta.className = "esp-field-input";
          ta.value = f.value || "";
          ta.placeholder = FIELD_LABELS[f.field_type] || f.field_type;
          box.appendChild(ta);
          fieldInputs[f.id] = { type: "value", required: !!f.required, el: ta };
        } else if (f.field_type === "date") {
          var di = document.createElement("input");
          di.type = "date";
          di.className = "esp-field-input";
          di.value = f.value || "";
          box.appendChild(di);
          fieldInputs[f.id] = { type: "value", required: !!f.required, el: di };
        } else if (f.field_type === "strikethrough") {
          box.classList.add("esp-field-static");
        } else {
          var inp = document.createElement("input");
          inp.type = f.field_type === "email" ? "email" : "text";
          inp.className = "esp-field-input";
          var defaultValue = f.value || "";
          if (!defaultValue && f.field_type === "name") defaultValue = pageData.signer_name || "";
          if (!defaultValue && f.field_type === "email") defaultValue = pageData.signer_email || "";
          inp.value = defaultValue;
          inp.placeholder = FIELD_LABELS[f.field_type] || f.field_type;
          box.appendChild(inp);
          fieldInputs[f.id] = { type: "value", required: !!f.required, el: inp };
        }

        pageWrap.appendChild(box);
      });
    }

    function renderDocument(readOnly) {
      var container = $("esp-pdf-pages");
      if (!container) return;
      container.innerHTML = '<div class="esp-pdf-status">Loading document…</div>';

      if (!window.pdfjsLib) {
        container.innerHTML = '<div class="esp-pdf-status">Could not load the PDF viewer.</div>';
        return;
      }
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = "/web/static/lib/pdfjs/build/pdf.worker.js";

      var fieldsByPage = {};
      (pageData.fields || []).forEach(function (f) {
        (fieldsByPage[f.page] = fieldsByPage[f.page] || []).push(f);
      });

      var url = pageData.pdf_url + (pageData.pdf_url.indexOf("?") === -1 ? "?" : "&") + "v=" + Date.now();

      window.pdfjsLib.getDocument(url).promise.then(function (pdf) {
        container.innerHTML = "";
        var pageCount = $("esp-page-count");
        if (pageCount) pageCount.textContent = pdf.numPages + (pdf.numPages === 1 ? " page" : " pages");

        var chain = Promise.resolve();
        var _loop = function (num) {
          chain = chain.then(function () {
            return pdf.getPage(num).then(function (page) {
              var containerWidth = container.clientWidth || 760;
              var unscaled = page.getViewport({ scale: 1 });
              var scale = containerWidth / unscaled.width;
              var viewport = page.getViewport({ scale: scale });

              var pageWrap = document.createElement("div");
              pageWrap.className = "esp-pdf-page";

              var canvas = document.createElement("canvas");
              canvas.width = viewport.width;
              canvas.height = viewport.height;
              pageWrap.appendChild(canvas);
              container.appendChild(pageWrap);

              return page.render({ canvasContext: canvas.getContext("2d"), viewport: viewport }).promise.then(function () {
                if (!readOnly) buildFieldOverlay(pageWrap, fieldsByPage[num] || []);
              });
            });
          });
        };
        for (var i = 1; i <= pdf.numPages; i++) _loop(i);
        return chain;
      }).catch(function () {
        container.innerHTML = '<div class="esp-pdf-status">Could not render the document preview.</div>';
      });
    }

    renderDocument(alreadySigned);

    if (alreadySigned) {
      $("esp-sign-card").style.display = "none";
      $("esp-success-card").style.display = "";
      return;
    }

    /* ================================================================
       Mode tabs (draw / type / upload)
       ================================================================ */
    var currentMode = "draw";
    document.querySelectorAll("#esp-mode-tabs .esp-tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        currentMode = tab.getAttribute("data-mode");
        document.querySelectorAll("#esp-mode-tabs .esp-tab").forEach(function (t) {
          t.classList.toggle("is-active", t === tab);
        });
        document.querySelectorAll(".esp-mode-panel").forEach(function (p) {
          p.classList.toggle("is-active", p.id === "esp-mode-" + currentMode);
        });
        updateSignBoxPreviews();
      });
    });

    /* ================================================================
       Draw signature
       ================================================================ */
    var canvas = $("esp-draw-canvas");
    var ctx = canvas.getContext("2d");
    ctx.lineWidth = 2.4;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#1e1b4b";
    var strokes = [];
    var currentStroke = null;
    var drawing = false;

    function canvasPoint(ev) {
      var rect = canvas.getBoundingClientRect();
      var clientX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      var clientY = ev.touches ? ev.touches[0].clientY : ev.clientY;
      return {
        x: (clientX - rect.left) * (canvas.width / rect.width),
        y: (clientY - rect.top) * (canvas.height / rect.height),
      };
    }

    function redraw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      strokes.forEach(function (stroke) {
        ctx.beginPath();
        stroke.forEach(function (pt, i) {
          if (i === 0) ctx.moveTo(pt.x, pt.y); else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();
      });
    }

    function startDraw(ev) {
      ev.preventDefault();
      drawing = true;
      currentStroke = [canvasPoint(ev)];
      strokes.push(currentStroke);
    }
    function moveDraw(ev) {
      if (!drawing) return;
      ev.preventDefault();
      currentStroke.push(canvasPoint(ev));
      redraw();
    }
    function endDraw() { drawing = false; currentStroke = null; updateSignBoxPreviews(); }

    canvas.addEventListener("mousedown", startDraw);
    canvas.addEventListener("mousemove", moveDraw);
    window.addEventListener("mouseup", endDraw);
    canvas.addEventListener("touchstart", startDraw, { passive: false });
    canvas.addEventListener("touchmove", moveDraw, { passive: false });
    canvas.addEventListener("touchend", endDraw);

    $("esp-draw-undo").addEventListener("click", function () {
      strokes.pop();
      redraw();
      updateSignBoxPreviews();
    });
    $("esp-draw-clear").addEventListener("click", function () {
      strokes = [];
      redraw();
      updateSignBoxPreviews();
    });

    /* ================================================================
       Type signature
       ================================================================ */
    var typeInput = $("esp-type-input");
    var typePreview = $("esp-type-preview");
    var TYPE_FONT_FAMILY = "'Brush Script MT', cursive";
    var TYPE_FONT_SIZE = 56;

    typeInput.addEventListener("input", function () {
      typePreview.textContent = typeInput.value || "Your signature preview";
      updateSignBoxPreviews();
    });

    function typedSignatureDataUrl() {
      var c = document.createElement("canvas");
      c.width = 520; c.height = 180;
      var tctx = c.getContext("2d");
      tctx.fillStyle = "#ffffff";
      tctx.fillRect(0, 0, c.width, c.height);
      tctx.fillStyle = "#1e1b4b";
      var text = typeInput.value || "";
      var fontSize = TYPE_FONT_SIZE;
      tctx.font = fontSize + "px " + TYPE_FONT_FAMILY;
      tctx.textBaseline = "middle";
      // Shrink to fit if a long name would overflow the fixed canvas width.
      var maxWidth = c.width - 48;
      var width = tctx.measureText(text).width;
      if (width > maxWidth) {
        fontSize = Math.max(18, Math.floor(fontSize * (maxWidth / width)));
        tctx.font = fontSize + "px " + TYPE_FONT_FAMILY;
      }
      tctx.fillText(text, 24, c.height / 2);
      return c.toDataURL("image/png");
    }

    /* ================================================================
       Upload signature
       ================================================================ */
    var uploadInput = $("esp-upload-input");
    var uploadPreview = $("esp-upload-preview");
    var uploadDataUrl = null;
    uploadInput.addEventListener("change", function () {
      var file = uploadInput.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function () {
        uploadDataUrl = reader.result;
        uploadPreview.src = uploadDataUrl;
        uploadPreview.style.display = "";
        $("esp-upload-label").textContent = file.name;
        updateSignBoxPreviews();
      };
      reader.readAsDataURL(file);
    });

    /* ================================================================
       Confirm & Sign
       ================================================================ */
    function getSignatureDataUrl() {
      if (currentMode === "draw") {
        if (!strokes.length) return null;
        return canvas.toDataURL("image/png");
      }
      if (currentMode === "type") {
        return typeInput.value.trim() ? typedSignatureDataUrl() : null;
      }
      return uploadDataUrl;
    }

    // Drop a live preview of the captured signature into every "Sign here" /
    // "Initial here" box the moment it changes, so it's obvious those boxes
    // are tied to the panel instead of looking inert until final submit.
    function updateSignBoxPreviews() {
      var dataUrl = getSignatureDataUrl();
      signBoxes.forEach(function (box) {
        var img = box.querySelector(".esp-field-sign-preview");
        var label = box.querySelector(".esp-field-sign-label");
        if (dataUrl) {
          if (!img) {
            img = document.createElement("img");
            img.className = "esp-field-sign-preview";
            box.insertBefore(img, box.firstChild);
          }
          img.src = dataUrl;
          box.classList.add("has-preview");
          if (label) label.style.display = "none";
        } else {
          if (img) img.remove();
          box.classList.remove("has-preview");
          if (label) label.style.display = "";
        }
      });
    }

    function collectFieldValues() {
      var values = {};
      Object.keys(fieldInputs).forEach(function (id) {
        var f = fieldInputs[id];
        values[id] = f.type === "checkbox" ? (f.el.checked ? "1" : "") : f.el.value;
      });
      return values;
    }

    function firstInvalidField() {
      var ids = Object.keys(fieldInputs);
      for (var i = 0; i < ids.length; i++) {
        var f = fieldInputs[ids[i]];
        if (!f.required) continue;
        var filled = f.type === "checkbox" ? f.el.checked : !!f.el.value.trim();
        if (!filled) return f.el;
      }
      return null;
    }

    $("esp-sign-btn").addEventListener("click", function () {
      var errEl = $("esp-error");
      errEl.style.display = "none";

      var invalidField = firstInvalidField();
      if (invalidField) {
        errEl.textContent = "Please fill in all required fields on the document before signing.";
        errEl.style.display = "";
        invalidField.scrollIntoView({ behavior: "smooth", block: "center" });
        invalidField.focus();
        return;
      }

      if (!$("esp-confirm-checkbox").checked) {
        errEl.textContent = "Please confirm you agree to sign electronically.";
        errEl.style.display = "";
        return;
      }
      var dataUrl = getSignatureDataUrl();
      if (!dataUrl) {
        errEl.textContent = "Please draw, type, or upload your signature first.";
        errEl.style.display = "";
        return;
      }

      var btn = $("esp-sign-btn");
      btn.disabled = true;
      btn.textContent = "Signing…";

      postForm("/hrsd/sign/" + pageData.token + "/submit", {
        signature_data: dataUrl,
        signature_type: currentMode,
        field_values: JSON.stringify(collectFieldValues()),
      }).then(function (data) {
        btn.disabled = false;
        if (!data.ok) {
          errEl.textContent = data.error || "Something went wrong. Please try again.";
          errEl.style.display = "";
          btn.textContent = "Confirm & Sign";
          return;
        }
        $("esp-sign-card").style.display = "none";
        var success = $("esp-success-card");
        success.style.display = "";
        success.classList.add("is-animating");
        // The final PDF was just regenerated server-side — re-render the
        // preview (read-only now) so the signer sees their own marks land,
        // instead of the pre-signing placeholders they started with.
        renderDocument(true);
      }).catch(function () {
        btn.disabled = false;
        btn.textContent = "Confirm & Sign";
        errEl.textContent = "Network error. Please try again.";
        errEl.style.display = "";
      });
    });

    /* ================================================================
       Reject flow
       ================================================================ */
    var rejectOverlay = $("esp-reject-overlay");
    $("esp-reject-btn").addEventListener("click", function () { rejectOverlay.classList.add("is-open"); });
    $("esp-reject-cancel").addEventListener("click", function () { rejectOverlay.classList.remove("is-open"); });
    $("esp-reject-confirm").addEventListener("click", function () {
      postForm("/hrsd/sign/" + pageData.token + "/reject", {
        reason: $("esp-reject-reason").value.trim(),
      }).then(function (data) {
        rejectOverlay.classList.remove("is-open");
        if (data.ok) {
          $("esp-sign-card").style.display = "none";
          $("esp-main").innerHTML = '<div class="esp-rejected-note">You have rejected this document. The sender has been notified.</div>';
        }
      });
    });
  });
})();
