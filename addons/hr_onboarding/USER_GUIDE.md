# HR Onboarding — User Guide

How HR runs onboarding day-to-day in this module, and where document/task
submission currently lives. This describes what is actually built today —
see **Not built yet** at the bottom for what's out of scope for now.

## 1. Where everything lives

Top app menu **HR Onboarding**:

| Menu | What it's for |
|---|---|
| Workspace Dashboard | KPIs, today's joiners, pending tasks, recent activity |
| New Hire Pipeline | Drag-and-drop stage board (the main HR workspace) |
| Onboarding Records | Plain list/form of every onboarding record |
| Documents | All documents across all candidates, card view |
| Tasks & Checklists | All tasks across all candidates, grouped by candidate |
| Equipment | All equipment across all candidates |
| Configuration → Pipeline Stages | Add/reorder stages, attach auto-emails |

## 2. The pipeline stages

A candidate moves left to right through 14 stages:

```
Lead → Interview → Offer Created → Offer Sent → Offer Accepted →
Documents Pending → Background Check → HR Approval → IT Setup →
Equipment Ready → Training → First Day → Probation → Completed
```

Two stages auto-send an email when a candidate enters them (configurable
under **Configuration → Pipeline Stages**, field "Auto-Send Email"):

- **Offer Sent** → sends the offer email
- **Documents Pending** → sends the "please submit your documents" email

## 3. HR's day-to-day flow

1. **Create Onboarding** (Dashboard quick action, or Onboarding Records →
   New). Fill in name, email, job, department, manager, buddy, assigned HR,
   joining date, priority. It's created in the **Lead** stage.
2. **Work the Pipeline** (New Hire Pipeline menu). Each card shows the
   candidate's photo/initials, department, joining countdown, progress ring,
   priority, and assigned HR. Drag a card to the next column to advance
   their stage — this is the same action as changing `stage_id` on the
   record, and it:
   - logs the stage change to the chatter (visible in Onboarding Records →
     open record → chatter/Activity Feed on the Journey screen)
   - writes a row to the stage-history log (used for the Journey timeline
     dates)
   - fires the stage's auto-email, if one is configured
3. **Open a candidate's Journey** (arrow icon on a pipeline card). Split
   view:
   - **Left**: profile card, progress ring, department/manager/buddy/HR
   - **Middle**: full stage timeline. Click a stage to expand it and see
     the tasks tied to that stage, plus (for "Documents Pending" /
     "Background Check") the document checklist.
   - **Right**: quick "Move to Next Stage" button, missing documents,
     pending tasks, activity feed.
4. **Tasks & Checklists** — add tasks per candidate (either from the Journey
   screen's expanded stage view, or the record's form → Tasks tab, or the
   global Tasks & Checklists menu). Each task has a name, due date,
   assignee, and a stage it belongs to (so it shows up under the right
   step of the Journey timeline).
5. **Documents** — same idea: add a document row per candidate (type —
   Passport / PAN / Aadhaar / Offer Letter / etc. — plus a status: Pending
   → Uploaded → Verified/Rejected). HR (or whoever has access) uploads the
   file and flips the status as it gets verified.
6. **Equipment** — same pattern: Laptop / Monitor / Access Card / etc.,
   with status Pending → Assigned → Delivered → Returned and an optional
   serial number.

## 4. Who submits documents

Candidates now upload their own documents from **outside Odoo**, no login
required, via a secure per-candidate link — this is the same "Submit
Documents" email flow from the reference screenshots.

**How it works:**

1. Every `hr.onboarding` record has a private `access_token` (generated
   automatically) and a computed **Document Submission Link**
   (`portal_document_url`) built from it — visible read-only on the
   candidate's form under "Document Portal".
2. **HR sends that link** by clicking **Send Document Request**. This is
   available in three places, so HR can send it any time, not just when
   the record automatically enters the "Documents Pending" stage:
   - the **Send Document Request** button on the candidate's form header
   - the envelope icon on the candidate's pipeline card
   - the "Send Document Request" button in the Journey screen's Quick
     Actions panel
   All three call the same `action_send_document_request()` method, which
   emails the existing "Onboarding: Document Request" template (now with
   the link baked into the button in the email body) and logs it to the
   chatter. This is in addition to the same email firing automatically the
   moment a record enters the **Documents Pending** stage (see §2) — HR can
   re-send it manually any time after that too, e.g. as a reminder.
3. **The candidate clicks the link** and lands on `/onboarding/documents/<token>`
   — a public page (no Odoo account needed) listing every document on
   their record. Pending/rejected documents get an upload box (click or
   drag-and-drop); already-uploaded/verified ones just show a checkmark.
   A required declaration checkbox ("I hereby declare that all submitted
   documents are true and legally valid...") sits above the submit button,
   matching the reference flow.
4. **On submit**, each uploaded file is written straight to the matching
   `hr.onboarding.document` row (status flips to Uploaded, upload date
   stamped), the declaration is recorded (`declaration_signed` /
   `declaration_date` fields on the onboarding record), and a chatter
   message logs how many documents came in — so it shows up in the
   candidate's Journey Activity Feed automatically.
5. HR then verifies each upload from the **Documents** workspace (flip
   status to Verified/Rejected) same as before.

Code, for reference: `models/hr_onboarding.py` (`access_token`,
`portal_document_url`, `action_send_document_request`),
`controllers/portal_controller.py` (the two public routes),
`views/templates_document_portal.xml` (the page), styled by
`static/src/css/document_portal.css` (a plain CSS file, not part of the
backend SCSS bundle, since this page is served standalone/unauthenticated).

**Security note:** the token is a random 32-character UUID acting as a
bearer credential — anyone with the link can upload as that candidate.
That's the same trust model as the reference screenshots' email link, but
if you need it to expire or be single-use, that's a follow-up (e.g. clear/
regenerate `access_token` once the record leaves "Documents Pending").

## 5. Dashboard KPIs, explained

| KPI | How it's computed |
|---|---|
| New Hires | count of all active onboarding records |
| Joining Today | `joining_date == today` |
| Pending Documents | documents with status Pending or Rejected |
| Equipment Pending | equipment with status Pending |
| Pending Tasks | tasks not marked done |
| Delayed Onboarding | `joining_date` has passed and stage isn't "Completed" |
| Completed Journeys | records in the "Completed" (final) stage |
| Avg. Completion (days) | average time-in-system for completed records |

## 6. Not built yet

Scoped out for now (see the original spec) — flag if you want any of these
next:

- AI/OCR document verification, resume parsing, chatbot
- Learning & Training, Buddy Program, Meetings, Email campaign designer
- IT Provisioning integrations (M365, Slack, GitHub, etc.)
- Reports/analytics beyond the dashboard KPIs
