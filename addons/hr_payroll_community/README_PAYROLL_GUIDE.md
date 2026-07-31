# Payroll — how it works & how to run it

This module turns `hr_payroll_community` into an automatic payroll system:
you set an employee's compensation once, everything else — worked days,
leave deductions, the salary breakdown, the payslip PDF, even the
accounting entry — is generated for you.

## 1. One-time setup per employee

Open **Payroll → Employees → (pick someone) → Payroll tab**.

1. **Wage** — set this to the employee's target **monthly Gross** (not CTC,
   not take-home — the Gross salary before employer contributions).
2. **Compensation Structure (% of Gross Wage)** — three percentages:
   - *Basic (% of Gross)* — default 50%
   - *HRA (% of Basic)* — default 40%
   - *CCA (% of Basic)* — default 20%
   - Everything else (Project & Special Allowance) is auto-computed as
     the balancing figure: `Gross − Basic − HRA − CCA − Medical`.
3. **Medical Allowance** — a fixed monthly amount (default ₹1,250).
4. **Statutory Contributions (EPF / LWF)** — EPF wage ceiling (₹15,000
   statutory default) and employee/employer/admin rates (12% / 12% / 1%
   by default). Adjust the admin rate if your payroll processor uses a
   different EDLI/admin charge convention than the statutory default.
5. **PAN / UAN / LWF Number** — statutory IDs, shown on the payslip and
   flagged on the Dashboard if missing.
6. Set the employee's **Structure** (Contract → Salary Structure) to
   **"India: Regular Pay"** — this is what tells the engine to actually
   apply the rules above. (New employees can also "Load a Template" from
   a pre-configured Contract Template that already has this structure.)

That's it — no more manual entry per payslip. Basic, HRA, CCA, Medical,
Project Allowance, EPF (all three legs) and the Total CTC are all
computed automatically from these few fields.

## 2. Timesheets & Time Off feed the payslip automatically

- If **HR Timesheet Pro** has an **approved** weekly timesheet covering
  (part of) the payslip's period, worked days/hours come from those
  logged hours.
- If there's no approved timesheet, it falls back to the employee's
  attendance/working calendar.
- Approved **Time Off** requests reduce paid days the same way they
  always did in this module — nothing new to configure.
- On a payslip, the **Worked Days** tab has a **"Refresh from Timesheets
  & Time Off"** button to pull this fresh at any time while in Draft.

## 3. Running a payslip

1. **Payroll → Employee Payslips → New**, pick the employee and period.
2. Click **Compute** (or **Refresh from Timesheets & Time Off** first,
   if you changed the period after creating it).
3. Check the **Salary Inputs** tab if this payslip needs a one-off
   **Bonus**, **TDS**, or **Additional Deduction** — these are the only
   things that still need manual entry, because they're genuinely
   variable per pay run (tax varies with income, bonuses aren't fixed
   compensation).
4. Click **Validate**. This locks the payslip, posts the accounting
   entry (see below), and generates the payslip PDF as the record's
   main attachment — which is what powers the preview panel next to the
   form.
5. Click **Pay** to record how and when it was paid (Payment Advice /
   NEFT / Cheque). **Print** downloads the PDF at any time.

## 4. Accounting entries (only if `hr_payroll_account_community` is installed)

Validating a payslip creates and posts an `account.move`. Out of the
box, this module gives the **Net Salary** rule a simple starting
default — **Debit** a "Salaries" (or generic Expense) account, **Credit**
a generic Payable account for your company — found automatically from
your chart of accounts the first time the module is installed, so a
fresh setup can validate a payslip immediately without a manual
accounting pass.

**This is a simplified single-line booking.** For a real payroll ledger
you'll usually want a proper breakdown — e.g. a dedicated *Salaries
Payable* account instead of generic Payable, separate *EPF Payable* /
*LWF Payable* liability accounts for the employer contributions, etc.
Go to **Payroll → Configuration → Salary Rules**, open the rule you
want to book separately (e.g. *Company EPF Share*), and set its own
Debit/Credit account — review this with your accountant before relying
on it for real books.

## 5. Dashboard & navigation

- **Payroll → Dashboard** is the landing page: employees on payroll, net
  payroll this period, pending actions (missing PAN/UAN/bank account,
  payslips without a running contract), and next pay date.
- **Time Offs** and **Employees** are one click away without leaving the
  Payroll app.

## 6. Known limitations / things that are intentionally manual

- **TDS / income tax** is not computed — Indian income tax depends on
  the employee's declared investments, regime choice, and cumulative
  YTD income, which this module doesn't model. Enter it as a payslip
  input each period.
- **EPF Admin/EDLI rate**: different payroll processors round this
  differently (statutory default vs. a company-specific practice) — if
  your issued payslips use a different admin charge, adjust the rate on
  the employee's contract to match.
- **Gratuity** shown on the Payroll tab is informational (an accrual
  estimate for planning), not deducted or paid out monthly.
- The accounting default (section 4) is a starting point, not a
  finished chart-of-accounts mapping — have it reviewed before go-live.

## 7. Validating the math yourself

If you want to sanity-check the engine against a real payslip: create
an employee with the real Gross wage, HRA/CCA/Basic percentages, and
Medical allowance from that payslip, log the matching timesheet hours,
create a payslip for that period, and compare — Basic/HRA/CCA/Medical/
Project Allowance/Gross/EPF/CTC should match to the rupee (Net will
also match once you enter the real TDS as a payslip input).

Total Paid Days (PAID_DAYS) = days actually worked (or assumed worked) + approved paid leave days, for the period you selected. It's built in get_worked_day_lines as:

PAID_DAYS = work_data['days'] + leave_days

Where:
- work_data['days'] — comes from approved HR Timesheet Pro entries in that period if any exist. If none exist (your case here, since hours = 23 × 8 = 184 exactly), it falls back to the working calendar, which assumes full attendance — i.e., every scheduled working day in the period counts as worked.
- leave_days — approved Time Off within the period, added on top (leave is still "paid").

So here: 23 = all the calendar's working days in that month, with no timesheet data to reduce it and no leave recorded — meaning the system is assuming 100% attendance because it has no real timesheet/attendance record to say otherwise. It equals WORKING_DAYS and WORK100 for the same reason: nothing in the data distinguishes "days scheduled" from "days actually present."

If you want PAID_DAYS to reflect real attendance instead of this "assume full attendance" fallback, that employee needs either approved HR Timesheet Pro entries or logged attendance for the period — otherwise you can just edit the number directly in this row (that's what the inline-edit + Add Line feature I added earlier is for).~