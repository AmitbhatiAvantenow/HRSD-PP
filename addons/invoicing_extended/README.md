# Invoicing Extended

Custom invoice fields, company settings and a modern branded PDF template
for staff-augmentation / consulting invoices (days/hours billing, AMC /
advance billing), built on top of Odoo's standard **Invoicing** app.

## 1. Install

1. Go to **Apps**.
2. Remove the default filter and search for `Invoicing Extended`.
3. Click **Install**.

The module depends only on `account` (Invoicing), so it installs on top of
whatever accounting setup you already have — nothing existing is removed
or altered.

## 2. One-time company setup

Go to **Settings → Users & Companies → Companies**, open your company,
and open the new **Extended Invoicing** tab.

| Field | What it's for |
|---|---|
| Invoice Tagline | Small text under the logo on the PDF, e.g. *"Quant Analytics with Agility"* |
| Default CCW Deduction (%) | Default deduction % pre-filled on new staff-augmentation invoices (editable per invoice) |
| Default LUT ARN | Default ARN quoted on export invoices raised under LUT (editable per invoice) |
| Authorized Signatory Name / Designation | Printed under "For \<Company Name\>" on every invoice |
| Authorized Signatory Signature | Signature image printed above the name/designation |

If you invoice from **more than one legal entity** (e.g. two group
companies), set these fields separately on each `res.company` record —
each company gets its own logo, tagline, signatory and defaults.

### Bank account IFSC code

Go to **Contacts → \[your company\] → Accounting → Bank Accounts**, open
the bank account used on your invoices, and fill in the new **IFSC Code**
field (next to Bank). SWIFT/BIC still comes from the standard Bank field.

## 3. Creating an invoice

Create a customer invoice as usual (**Accounting/Invoicing → Customers →
Invoices → New**), then open the new **Extended Invoice** tab on the
invoice form.

### Layout & Subject
- **Extended Invoice Layout** — pick one:
  - **Staff Augmentation (Days/Hours based)** — for consultant billing
    (shows Days Worked / Hourly Rate / Hours Worked / CCW deduction on
    the PDF).
  - **Simple / Advance / AMC** — for flat-fee invoices like AMC/support
    renewals (shows a plain Description/Amount table, no CCW block).
- **Invoice Subject** — free text shown under the invoice number, e.g.
  `June '26 Services by Abhishek R - Purchase Order #810013986`.
- **Client PO Number**
- **Invoice Reference Number** — auto-generated, read-only, unique per
  invoice.

### Bill To Contact
- **Kind Attn** — the named contact person at the client.
- **CC Details** — free text, printed under Bill To.

### Consultant / Assignment *(Staff Augmentation layout only)*
- Consultant Name, Job Role, Service Period (e.g. `June '26`)
- Days Worked, Hours per Day (default 8), Hourly Rate
- Hours Worked is computed automatically (`Days Worked × Hours per Day`)

### Deductions *(Staff Augmentation layout only)*
- **CCW Deduction (%)** — pre-filled from the company default, editable.
- CCW Deduction Amount and Final Assessable Value are computed
  automatically from Hourly Rate x Hours Worked, and — with a single
  product line on the invoice — applied as that line's discount, so the
  invoice's real Untaxed Amount / Total / Amount Due match the Final
  Assessable Value too (see §6).

### Export / Compliance
- **Supply under LUT** — tick for export invoices without IGST; reveals
  the **LUT ARN** field.
- **Reverse Charge Applicable** — Yes/No.
- **Authorized Signatory** — defaults from the company, editable per
  invoice if a different person signs this one.

Then add your **Invoice Lines** as normal (product, quantity, price,
taxes — this is standard Odoo and drives the real accounting/GST amounts).

## 4. Printing the PDF

On a saved invoice, click **Print → Extended Invoice** (it appears
automatically in the Print menu, alongside Odoo's standard "Invoice
PDF"). The document works in whatever currency the invoice uses (INR,
USD, EUR, AED, ...) — nothing extra to configure per currency.

## 5. What's on the PDF

- Company logo, tagline and "Tax Invoice" / "Credit Note" title
  (with the LUT export line shown automatically when applicable)
- Invoice number, date, PO number, subject
- Company address & GST/VAT block
- Bill To block (Kind Attn, client address, GSTIN/VAT, CC)
- Invoice Reference Number
- Line items table (columns depend on the chosen layout)
- Totals: Total Assessable Value → CCW Deduction → Final Assessable
  Value → real tax lines (CGST/SGST/IGST, from your actual Odoo taxes)
  → Total Payable
- ARN for LUT, Reverse Charge Yes/No, Amount in Words
- Bank details (from the invoice's **Recipient Bank** field), shown in a
  highlighted box
- Signature block: "For \<Company\>", signature image, signatory name
  and designation

## 6. Important note on the CCW deduction

For the Staff Augmentation layout, entering **Hourly Rate**, **Days
Worked** / **Hours per Day** and a **CCW Deduction (%)** drives the real
invoice line: quantity = Hours Worked, unit price = Hourly Rate, and the
CCW % is applied as the line's discount. That means the actual accounting
totals (Untaxed Amount / Total / Amount Due on the invoice, and the taxes
computed on it) already reflect the Final Assessable Value shown on the
Extended Invoice PDF — the printed "Total Payable" and Odoo's own "Amount
Due" match. This only applies when there's a single product line on the
invoice; with multiple product lines the fields still compute and print
correctly, but quantity/price/discount aren't auto-synced onto any one
line, so set the line(s) directly if you're not using the single-line
convenience path.

## 7. Field reference (technical)

All new fields live on `account.move` unless noted, and are all optional
— nothing is required to save or post an invoice.

| Field (technical name) | Type |
|---|---|
| `invoice_layout` | Selection: `staff_augmentation` / `advance_simple` |
| `consultant_name`, `job_role`, `service_period`, `client_po_number`, `invoice_subject` | Char |
| `kind_attn` | Char |
| `cc_details` | Text |
| `days_worked`, `hours_per_day` | Float |
| `hourly_rate` | Monetary |
| `hours_worked` | Float (computed) |
| `ccw_deduction_percent` | Float |
| `gross_assessable_value`, `ccw_deduction_amount`, `final_assessable_value`, `extended_grand_total` | Monetary (computed) |
| `is_export_under_lut` | Boolean |
| `lut_arn` | Char |
| `reverse_charge_applicable` | Selection: `yes` / `no` |
| `invoice_reference_hash` | Char (auto-generated, read-only) |
| `authorized_signatory_name`, `authorized_signatory_designation` | Char |
| `res.company.invoice_tagline`, `invoice_default_ccw_percent`, `invoice_default_lut_arn`, `invoice_signatory_name`, `invoice_signatory_designation`, `invoice_signatory_signature` | company-level defaults |
| `res.partner.bank.ifsc_code` | Char |
