# -*- coding: utf-8 -*-
{
    "name": "HR Plus | FREE | Document Expiry · Asset Assignment · Onboarding · Career · Disciplinary · Loans · EOSB · MENA-Ready",
    "version": "19.0.3.2.0",
    "category": "Human Resources",
    "summary": "FREE 12-feature HR add-on covering everything missing from Odoo Enterprise. "
               "Document expiry tracker (Iqama / passport / visa / driver's licence / work permit / medical) with cron alerts. "
               "Asset assignment (laptop / phone / SIM / access card / uniform) with check-out / return. "
               "Onboarding + offboarding checklists. Career history (promotion / transfer / salary). "
               "Disciplinary actions (warning / suspension / termination). "
               "Employee loans with installment schedule. "
               "Dependents (spouse / children). "
               "End-of-Service Benefits (EOSB / gratuity) calculator — KSA + UAE labor law. "
               "Probation tracking. Business trips. Policy acknowledgements. "
               "OWL HR Ops dashboard with expiring document alerts + probation ending soon + active loans + open assets.",
    "description": """
HR Plus for Odoo 19 — FREE (LGPL-3)
====================================
12 features the Odoo Enterprise HR module doesn't have, that any
HR team in the MENA region needs from day one.

* **Document Tracker** — Iqama / passport / visa / driver's licence /
  work permit / medical insurance card / health certificate. Each
  document has issue date, expiry date, scan upload, country of issue.
  Cron fires alerts at 90 / 60 / 30 / 14 / 7 days before expiry.
* **Asset Assignment** — Laptop / phone / SIM card / access badge /
  uniform / vehicle / other. Issue date, return date, condition on
  return, signed handover.
* **Onboarding Checklist** — 12-task template per new employee:
  contract signed, visa initiated, bank account opened, ID issued,
  laptop assigned, training scheduled, etc. State per task.
* **Offboarding Checklist** — exit interview, asset return, final
  settlement, access revoked, knowledge handover.
* **Career History** — promotion · transfer · salary change · job-title
  change. Full audit with effective date + approved by + reason.
* **Disciplinary Actions** — verbal warning · written warning ·
  suspension · termination. 4-state machine, attached document.
* **Employee Loans** — principal + interest + months + auto-generated
  installment schedule. Payment marker (paid / pending / overdue).
* **Dependents** — spouse · children · parents. Name, DOB, relation,
  passport, visa, dependent allowance flag.
* **End-of-Service Benefits (EOSB)** — Saudi + UAE labor-law calculator.
  Half-month per year for first 5 years, full month thereafter
  (Saudi formula). Computes from start date + last salary.
* **Probation Period** — extend / pass / fail. Cron alerts manager
  14 / 7 / 1 days before probation ends.
* **Business Trips** — destination / dates / purpose / advance / per
  diem / reimbursement. State machine with manager approval.
* **Policy Acknowledgements** — upload company handbook + per-policy
  required-by-role flag. Track who read + signed which policy.

* **OWL HR Ops dashboard** — 8 KPI tiles · documents expiring next 30 days
  · probation ending soon · active loans · assets out · disciplinary
  open · recent hires. Auto-refresh.

Pricing
-------
**FREE.** LGPL-3 license. Lifetime updates.
    """,
    "author": "Moaz Nabil",
    "website": "https://github.com/moaaznaabilali",
    "support": "moaaznaabilali@gmail.com",
    "license": "LGPL-3",
    "price": 0.00,
    "currency": "USD",
    "depends": ["base", "mail", "web", "hr"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequences.xml",
        "data/document_type_data.xml",
        "data/asset_category_data.xml",
        "data/onboarding_task_data.xml",
        "data/policies_data.xml",
        "data/cron.xml",
        "views/document_tracker_views.xml",
        "views/asset_assignment_views.xml",
        "views/onboarding_views.xml",
        "views/offboarding_views.xml",
        "views/career_history_views.xml",
        "views/disciplinary_views.xml",
        "views/loan_views.xml",
        "views/dependent_views.xml",
        "views/eosb_views.xml",
        "views/probation_views.xml",
        "views/business_trip_views.xml",
        "views/policy_views.xml",
        "views/hr_employee_views.xml",
        "views/dashboard_action.xml",
        "views/training_views.xml",
        "views/okr_views.xml",
        "views/feedback360_views.xml",
        "views/exit_views.xml",
        "views/referral_views.xml",
        "views/recognition_views.xml",
        "views/letter_views.xml",
        "views/suggestion_views.xml",
        "views/visa_views.xml",
        "reports/letter_report.xml",
        "wizards/eosb_calculator_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
              "hr_plus/static/src/scss/backend.scss",
              "hr_plus/static/src/dashboard/dashboard.js",
              "hr_plus/static/src/dashboard/dashboard.xml",
              "hr_plus/static/src/dashboard/people.js",
              "hr_plus/static/src/dashboard/people.xml",
              "hr_plus/static/src/dashboard/training.js",
              "hr_plus/static/src/dashboard/training.xml",
              "hr_plus/static/src/dashboard/engagement.js",
              "hr_plus/static/src/dashboard/engagement.xml",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
