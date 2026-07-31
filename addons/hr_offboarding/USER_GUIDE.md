# HR Offboarding — User Guide

How HR runs an employee exit day-to-day in this module. This describes
what is actually built today — see **Not built yet** at the bottom for
what's out of scope for now.

## 1. Where everything lives

Top app menu **HR Offboarding**:

| Menu | What it's for |
|---|---|
| Workspace Dashboard | KPIs, today's exits, pending tasks, recent activity |
| Exit Pipeline | Drag-and-drop stage board (the main HR workspace) |
| Exit Requests | Plain list/form of every exit request |
| Clearance Center | Department sign-offs (HR, Finance, IT, Admin, Security, Facilities, Legal, Manager), grouped by department |
| Asset Returns | All assets across all exits, card view |
| Tasks & Checklists | All tasks across all exits, grouped by exit request |
| Documents | Experience letter, relieving letter, settlement letter, etc. |
| Payroll Settlement | Full & final settlement records |
| Exit Interviews | Exit interview questionnaires |
| Configuration → Exit Stages | Add/reorder stages, attach auto-emails |

## 2. The exit stages

An exit request moves left to right through 12 stages:

```
Resignation Submitted → Manager Review → HR Review → Exit Approved →
Knowledge Transfer → Asset Collection → IT Deprovisioning →
Payroll Settlement → Exit Interview → Experience Letter →
Relieving Letter → Completed
```

Three stages auto-send an email when a request enters them (configurable
under **Configuration → Exit Stages**, field "Auto-Send Email"):

- **Resignation Submitted** → acknowledgement email (with last working day)
- **Exit Approved** → clearance reminder (coordinate with HR/Finance/IT/etc.)
- **Payroll Settlement** → "your settlement is ready" email

## 3. HR's day-to-day flow

1. **Create Exit Request** (Dashboard quick action, or Exit Requests →
   New). Pick the departing **Employee** — job, department and manager
   auto-fill from their employee record via onchange. Fill in resignation
   date, last working day, notice period, exit reason, priority, assigned
   HR. It's created in the **Resignation Submitted** stage.
2. **Work the Pipeline** (Exit Pipeline menu). Each card shows the
   employee's initials, department, countdown to last working day,
   progress ring, priority, and assigned HR. Drag a card to the next
   column to advance the stage — same as changing `stage_id` on the
   record, and it:
   - logs the stage change to the chatter
   - writes a row to the stage-history log (used for the Journey timeline
     dates)
   - fires the stage's auto-email, if one is configured
3. **Open an employee's Exit Journey** (arrow icon on a pipeline card).
   Split view:
   - **Left**: profile card, progress ring, department/manager/successor/
     notice period/last working day/assigned HR
   - **Middle**: full stage timeline. Click a stage to expand it and see
     the tasks tied to that stage, plus (depending on the stage) the
     department clearance checklist, asset return checklist, document
     checklist, or settlement summary.
   - **Right**: "Move to Next Stage" button, missing approvals, missing
     assets, pending tasks, activity feed.
4. **Clearance Center** — one row per department (HR/Finance/IT/
   Administration/Security/Facilities/Legal/Manager) per exit request.
   Each department clears independently with Approve/Reject buttons
   (`action_approve` / `action_reject`, stamping approver + timestamp).
   Only one clearance row per (request, department) pair is allowed.
5. **Asset Returns** — one row per item (Laptop, Monitor, Access Card,
   Phone, etc.) with status Pending → Returned (or Damaged/Lost), serial
   number, condition, and an optional replacement cost if something isn't
   returned in good shape.
6. **Payroll Settlement** — one settlement record per exit request:
   earnings (leave encashment, pending salary, bonus, incentives,
   gratuity) minus deductions (loans, recoveries, tax, PF) = net
   settlement, all computed automatically. Status Draft → Generated →
   Approved → Paid.
7. **Exit Interviews** — a simple questionnaire per request: primary exit
   reason, overall rating (1–5), manager feedback, company feedback,
   suggestions, anonymous-mode flag. Status Scheduled → Completed/Skipped.
8. **Documents** — generate/track Experience Letter, Relieving Letter,
   Settlement Letter, Tax Certificate, Clearance Certificate, No Due
   Certificate, Service Certificate, Salary History — same
   pending → generated → verified/rejected flow as onboarding's documents.
9. **Tasks & Checklists** — covers both Knowledge Transfer tasks (project
   handover, repo access transfer, successor briefing) and IT
   Deprovisioning tasks (revoke M365/VPN/GitHub/etc.) — every task just
   has a name, due date, assignee, and the exit stage it's tied to, so it
   surfaces under the right step of the Exit Journey timeline.

## 4. Who submits documents / handles clearance today

**Unlike onboarding, there's no public self-service portal for departing
employees yet** — everything here (clearance approvals, asset status,
document uploads, settlement figures, interview notes) is entered by HR
or the relevant department from inside Odoo. If/when you want an
employee-facing piece (e.g. a portal page for the departing employee to
view their clearance progress, or a link for department approvers to
sign off without logging in), that's the same pattern already built for
`hr_onboarding` (a token field + public controller + qweb page) — just not
wired up here yet since it wasn't needed for this pass. Say the word and
it can be layered onto `hr.offboarding.clearance` /
`hr.offboarding.document` the same way.

## 5. Dashboard KPIs, explained

| KPI | How it's computed |
|---|---|
| Employees Leaving | count of all active exit requests |
| Today's Exits | `last_working_day == today` |
| Pending Approvals | clearance rows with status Pending or Needs Action |
| Pending Asset Returns | assets with status Pending |
| Payroll Pending | settlement records with status other than Paid |
| Pending Tasks | tasks not marked done |
| Delayed Offboarding | `last_working_day` has passed and stage isn't "Completed" |
| Completed Offboarding | records in the "Completed" (final) stage |

## 6. Not built yet

Scoped out for now (see the original spec) — flag if you want any of these
next:

- Employee/approver-facing public portal (same pattern as onboarding's
  document portal — see §4)
- AI features: attrition prediction, sentiment analysis, exit summary
  generation, policy RAG chatbot
- IT Deprovisioning integrations (M365, Slack, GitHub, Azure, AWS, etc. —
  currently just plain tasks, not live API calls)
- Email campaign designer, Communications timeline as a separate app
- Reports/analytics beyond the dashboard KPIs
- Digital signature / QR verification on generated documents
