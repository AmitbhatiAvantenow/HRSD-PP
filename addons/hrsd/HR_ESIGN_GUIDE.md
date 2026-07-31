# HR Sign — Guide

A DocuSign-style e-signature app running inside this Odoo Community instance (module: `hrsd`).
This guide covers what was built, how to install/access it, how the two user journeys work,
the data model, and what's intentionally out of scope for now.

---

## 1. What this is

"HR Sign" lets HR create a document (offer letter, NDA, contract, policy ack, appraisal form),
send it to one or more people for signature, and track everything — pending/completed/rejected —
from one dashboard. Signers get a secure emailed link, no Odoo login required, and sign on a
DocuSign-style split-screen page (PDF preview + draw/type/upload signature).

It is a real feature, not a mockup: every action writes to normalized Odoo models, not just the
frontend. The frontend (OWL components inside the backend, plain HTML/JS for the public signing
page) is presentation-only.

---

## 2. Installing / updating

After pulling these changes, the module needs a DB update (new models, views, menu) and a server
restart (new Python).

```
! /path/to/odoo-bin -c <your-config> -u hrsd --stop-after-init
```

Then restart the server normally. If you don't have a config file, pass `-d <your-db>` instead of
`-c`.

---

## 3. Accessing it

**HR / internal users:**
```
http://localhost:8069/odoo
```
Log in → click the apps grid icon (top-left) → **HR Sign**. That opens the landing dashboard.

Sub-menus (also reachable from the dashboard's quick-action cards):
- **Dashboard** — the landing page (KPIs, quick actions, recent activity)
- **Documents** — list/kanban/form of every `hr.esign.document`
- **Templates** — reusable source documents
- **Audit Logs** — full event trail across all documents

**Signers (external recipients):**
```
http://localhost:8069/hrsd/sign/<token>
```
Generated per-signer, per-document, and emailed automatically when a document is sent — you never
type this by hand. To find one manually for testing: open a document's **Signers** tab in the
backend, look at the `token` field on a signer row.

---

## 4. HR journey (creating & sending a document)

1. From the **Dashboard**, click **Create Document** (hero button or quick-action card).
2. A 4-step wizard opens:
   - **Choose Employee** — who the document is for. They're auto-added as the first signer.
   - **Template / Upload** — pick a saved template, or upload a PDF/DOCX. On upload, the file is
     analyzed immediately (`hr.esign.document.ai_analyze_file`): suggested category, suggested
     title, and a duplicate-document warning if a file with the same content hash already exists.
   - **Workflow** — parallel or sequential signing, add/remove signers (pick an employee or type a
     name/email for an external signer), due date, priority.
   - **Review** — summary of everything above.
3. **Save Draft** creates the record without sending. **Send for Signature** creates it and
   immediately emails every signer their signing link (`hr.esign.signer._send_signing_email`),
   moving the document to `in_progress`.
4. Track progress from the **Documents** workspace (kanban/list) or the dashboard's recent-activity
   timeline — every view/sign/reject/reminder is logged to the **Audit Logs**.
5. Once every signer has signed, the document auto-completes (`state = completed`,
   `completed_date` set). You can then **Archive** it from the form view.

---

## 5. Employee / signer journey

1. Signer receives an email with a **Review & Sign** button.
2. Opens `/hrsd/sign/<token>` — no Odoo account needed. First open marks the signer as `viewed`.
3. Sees the document (PDF preview, left) and the signer/document info panel (right).
4. Adds a signature via **Draw** (canvas), **Type** (rendered in a signature-style font), or
   **Upload** (their own image file) — all three normalize to the same PNG format on submit.
5. Must tick the "legally binding" consent checkbox, then **Confirm & Sign**.
   - Or **Reject** with an optional reason — this sets the whole document to `rejected`.
6. On success: animated confirmation screen + **Download Signed Copy** link (the original PDF with
   an appended Certificate of Completion page — signer name/email, timestamp, IP, signature image).
7. A confirmation email with the same download link is sent automatically
   (`hr.esign.signer._send_confirmation_email`).
8. If the document had other pending signers, it stays `in_progress`; once all have signed it moves
   to `completed` and HR sees that reflected on the dashboard.

---

## 6. Data model

| Model | Purpose | Key fields |
|---|---|---|
| `hr.esign.document` | The envelope being signed | `code` (auto), `name`, `category`, `employee_id`, `file_data`, `file_hash` (dup detection), `extracted_text`, `template_id`, `workflow_type`, `state`, `signer_ids`, `audit_ids`, `progress` (computed %) |
| `hr.esign.signer` | One row per required signature | `document_id`, `sequence`, `employee_id`, `name`, `email`, `status`, `token` (secure link), `signature_data`, `signature_type`, `ip_address` |
| `hr.esign.template` | Reusable source documents | `name`, `category`, `file_data`, `usage_count`, `is_pinned` |
| `hr.esign.audit.log` | Immutable event trail | `document_id`, `event_type`, `description`, `actor_name`, `user_id` |

`hr.esign.document` inherits `mail.thread` (chatter-ready, though no chatter widget is wired into
the form view yet — easy to add with `<div class="oe_chatter">` if you want it).

---

## 7. AI / document-intelligence features

Everything below runs **offline** — no external AI API key, no network call. Built entirely on
packages already installed in this environment (`pytesseract`, `pdfminer.six`, `python-docx`,
`scikit-learn`, `rapidfuzz`) by reusing this addon's existing OCR/resume-parsing pipeline.

| Feature | How it actually works |
|---|---|
| OCR / text extraction | `pdfminer` for PDF text layers, `python-docx` for Word, UTF-8 decode fallback for plain text |
| Document classification | Keyword scoring against a small category dictionary (offer letter, contract, NDA, policy, appraisal) |
| Duplicate detection | SHA-256 hash of the raw file bytes, compared against every existing document |
| Metadata extraction | First non-empty line of extracted text as a suggested title |
| Intelligent search | Keyword-frequency scoring over title + extracted text (`search_documents_smart`) |
| Smart reminders | Daily cron nudges signers idle 3+ days on an in-progress document, and flags documents past `due_date` as `expired` |

**Not built — needs infrastructure this environment doesn't have:**
- True RAG / semantic search over HR policies. That needs an embeddings model + an LLM API
  (OpenAI/Anthropic/etc.) — no key or network access is configured here. What exists (keyword
  search) is a genuine, working stand-in, not a disguised fake.
- Scanned-image OCR *within* the e-sign upload flow specifically (the wizard's `ai_analyze_file`
  only reads born-digital PDF/DOCX text, not photographed/scanned pages). The separate "OCR Document
  Scanner" feature elsewhere in this addon *does* have full `pytesseract` image OCR — wiring that
  into e-sign uploads is a small, contained follow-up if you want it.

---

## 8. Email setup (required for real delivery)

Signing-request emails, reminders, and confirmation emails all go through `mail.mail`. For them to
actually leave the server you need an **Outgoing Mail Server** configured:
Settings → Technical → Email → Outgoing Mail Servers.

Without one, Odoo will queue the emails but they won't send — you can still test the whole flow by
grabbing the signer's `token` directly from the Signers tab and visiting `/hrsd/sign/<token>`
yourself.

(Separately, the earlier "RCHR" inbound-email-to-recruitment feature needs an **Incoming** Mail
Server — that's a different, unrelated pipeline from this one.)

---

## 9. Known limitations / good next steps

- **No pixel-precise signature placement.** DocuSign lets you drag a signature box onto an exact
  spot on the PDF. Here, signing is per-document (one signature captured per signer, stamped onto a
  certificate page appended at the end) rather than per-coordinate. Building true drag-and-drop
  field placement means a PDF.js canvas overlay with a page-coordinate system — a meaningfully
  larger project on its own.
- **Reports / Configuration** quick-action cards currently show a "coming soon" toast — not built
  out yet.
- **No chatter widget** on the document form view (model supports it via `mail.thread`, just not
  wired into the view).
- Classification/metadata extraction are **heuristics**, not machine-learned — they'll be wrong on
  unusually formatted documents. Worth tuning `_CATEGORY_KEYWORDS` / `_LABEL_PATTERNS` in
  `models/hr_esign.py` and `controllers/recruitment_controller.py` as real documents surface edge
  cases.

---

## 10. Where things live (for future changes)

```
addons/hrsd/
├── models/hr_esign.py                        # Document/Signer/Template/AuditLog + AI methods
├── controllers/esign_controller.py            # Public signing portal routes + PDF certificate gen
├── views/hr_esign_views.xml                   # List/kanban/form views, actions, menu
├── views/hr_esign_portal_templates.xml        # Public signing page (server-rendered QWeb)
├── data/hr_esign_data.xml                     # Sequence + reminder cron
├── security/ir.model.access.csv               # Access rows (search "hr_esign")
├── static/src/hr_esign/dashboard/              # OWL landing dashboard (js/xml/scss)
├── static/src/hr_esign/wizard/                 # OWL create-document wizard (js/xml/scss)
├── static/src/js/esign_portal.js               # Public portal signature pad (vanilla JS)
└── static/src/css/esign_portal.css             # Public portal styling
```
