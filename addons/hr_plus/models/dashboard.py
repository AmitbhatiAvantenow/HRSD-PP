# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models


class HRPlusDashboard(models.TransientModel):
    _name = "mn.hr.plus.dashboard"
    _description = "HR Plus Dashboard"

    @api.model
    def data(self):
        today = fields.Date.today()
        soon30 = today + timedelta(days=30)
        Doc = self.env["mn.hr.document.tracker"].sudo()
        Prob = self.env["mn.hr.probation"].sudo()
        Loan = self.env["mn.hr.loan"].sudo()
        Asset = self.env["mn.hr.asset.assignment"].sudo()
        Dis = self.env["mn.hr.disciplinary.action"].sudo()
        Emp = self.env["hr.employee"].sudo()

        expiring = Doc.search([("expiry_date", ">=", today), ("expiry_date", "<=", soon30)])
        expired = Doc.search([("expiry_date", "<", today)])
        prob_soon = Prob.search([("state", "in", ("active", "review_due")),
                                  ("end_date", "<=", soon30)])
        active_loans = Loan.search([("state", "in", ("active", "disbursed"))])
        open_assets = Asset.search([("state", "=", "assigned")])
        open_disc = Dis.search([("state", "in", ("issued", "acknowledged"))])
        recent = Emp.search([("create_date", ">=", today - timedelta(days=30))], limit=15)
        birthdays = Emp.search([])
        bdays = [e for e in birthdays if e.birthday and
                  e.birthday.month == today.month and
                  e.birthday.day in range(today.day, today.day + 7)]

        return {
            "kpis": {
                "expiring_30d": len(expiring),
                "expired": len(expired),
                "probation_soon": len(prob_soon),
                "active_loans": len(active_loans),
                "loan_outstanding": round(sum(active_loans.mapped("remaining_amount")), 2),
                "open_assets": len(open_assets),
                "open_disciplinary": len(open_disc),
                "birthdays_week": len(bdays),
            },
            "expiring": [{
                "id": d.id, "employee": d.employee_id.name,
                "doc": d.document_type_id.name,
                "expiry": fields.Date.to_string(d.expiry_date),
                "days": d.days_to_expiry,
                "state": d.state,
            } for d in expiring.sorted("days_to_expiry")[:12]],
            "probation": [{
                "id": p.id, "employee": p.employee_id.name,
                "end_date": fields.Date.to_string(p.end_date),
                "days": p.days_remaining,
            } for p in prob_soon.sorted("days_remaining")[:10]],
            "loans": [{
                "id": l.id, "employee": l.employee_id.name,
                "principal": l.principal,
                "remaining": l.remaining_amount,
                "months": l.months,
            } for l in active_loans[:10]],
            "recent_hires": [{
                "id": e.id, "name": e.name,
                "job_title": e.job_title or "",
                "department": e.department_id.name or "",
                "hired": fields.Date.to_string(e.create_date.date() if e.create_date else False),
            } for e in recent],
        }

    # ---------- People Analytics ----------
    @api.model
    def people_data(self):
        Emp = self.env["hr.employee"].sudo()
        emps = Emp.search([])
        today = fields.Date.today()

        # By department
        by_dept = {}
        for e in emps:
            k = e.department_id.name or "Unassigned"
            by_dept[k] = by_dept.get(k, 0) + 1

        # By gender (robust to different hr.employee schemas)
        by_gender = {"male": 0, "female": 0, "other": 0}
        for e in emps:
            # Try common gender fields: selection `gender` or m2o `gender_id`
            g = getattr(e, "gender", None)
            if not g:
                grec = getattr(e, "gender_id", None)
                if grec:
                    g = getattr(grec, "name", str(grec))
            # Normalize to male/female/other
            if g:
                g_str = str(g).lower()
                if g_str in ("male", "m", "man"):
                    key = "male"
                elif g_str in ("female", "f", "woman"):
                    key = "female"
                else:
                    key = "other"
            else:
                key = "other"
            by_gender[key] = by_gender.get(key, 0) + 1

        # Tenure buckets (years)
        buckets = {"<1y": 0, "1-3y": 0, "3-5y": 0, "5-10y": 0, "10y+": 0}
        for e in emps:
            ref = e.create_date and e.create_date.date()
            if not ref:
                continue
            years = (today - ref).days / 365.25
            if years < 1: buckets["<1y"] += 1
            elif years < 3: buckets["1-3y"] += 1
            elif years < 5: buckets["3-5y"] += 1
            elif years < 10: buckets["5-10y"] += 1
            else: buckets["10y+"] += 1

        # Age buckets
        age_buckets = {"<25": 0, "25-34": 0, "35-44": 0, "45-54": 0, "55+": 0, "unknown": 0}
        for e in emps:
            if not e.birthday:
                age_buckets["unknown"] += 1; continue
            a = (today - e.birthday).days / 365.25
            if a < 25: age_buckets["<25"] += 1
            elif a < 35: age_buckets["25-34"] += 1
            elif a < 45: age_buckets["35-44"] += 1
            elif a < 55: age_buckets["45-54"] += 1
            else: age_buckets["55+"] += 1

        # Hires last 12 months by month
        hires = {}
        for e in emps:
            if not e.create_date:
                continue
            d = e.create_date.date()
            if (today - d).days <= 365:
                key = d.strftime("%Y-%m")
                hires[key] = hires.get(key, 0) + 1
        hires_series = sorted(hires.items())

        # Headcount summary
        active = len(emps)
        exited = len(self.env["mn.hr.exit.interview"].sudo().search([
            ("interview_date", ">=", today - timedelta(days=365))]))
        return {
            "kpis": {
                "headcount": active,
                "departments": len(set(emps.mapped("department_id"))),
                "managers": len(set(e.parent_id.id for e in emps if e.parent_id)),
                "exits_12m": exited,
                "avg_tenure_y": round(sum((today - (e.create_date.date() if e.create_date else today)).days
                                          for e in emps) / max(1, active) / 365.25, 1),
                "gender_male": by_gender.get("male", 0),
                "gender_female": by_gender.get("female", 0),
            },
            "by_dept": sorted(by_dept.items(), key=lambda x: -x[1])[:10],
            "tenure_buckets": list(buckets.items()),
            "age_buckets": list(age_buckets.items()),
            "hires_series": hires_series,
        }

    # ---------- Training & Compliance ----------
    @api.model
    def training_data(self):
        T = self.env["mn.hr.training"].sudo()
        today = fields.Date.today()
        soon = today + timedelta(days=30)
        all_t = T.search([])
        mandatory = T.search([("is_mandatory", "=", True)])
        mand_done = mandatory.filtered(lambda r: r.state == "completed")
        expiring = T.search([("certificate_expiry", ">=", today),
                              ("certificate_expiry", "<=", soon),
                              ("state", "=", "completed")])
        expired = T.search([("state", "=", "expired")])

        # By category hours
        by_cat = {}
        for t in all_t:
            k = dict(T._fields["category"].selection).get(t.category, t.category or "other")
            by_cat[k] = by_cat.get(k, 0) + (t.duration_hours or 0)

        # Per-employee top consumers
        per_emp = {}
        for t in all_t.filtered(lambda r: r.state == "completed"):
            per_emp[t.employee_id.name] = per_emp.get(t.employee_id.name, 0) + (t.duration_hours or 0)
        top_learners = sorted(per_emp.items(), key=lambda x: -x[1])[:8]

        return {
            "kpis": {
                "total_trainings": len(all_t),
                "completed": len(all_t.filtered(lambda r: r.state == "completed")),
                "ongoing": len(all_t.filtered(lambda r: r.state == "ongoing")),
                "mandatory_total": len(mandatory),
                "mandatory_done": len(mand_done),
                "compliance_pct": round(len(mand_done) / max(1, len(mandatory)) * 100, 1),
                "expiring_30d": len(expiring),
                "expired": len(expired),
                "total_hours": round(sum(all_t.mapped("duration_hours") or [0]), 1),
                "total_cost": round(sum(all_t.mapped("cost") or [0]), 2),
            },
            "expiring": [{
                "id": r.id, "employee": r.employee_id.name, "title": r.title,
                "expiry": fields.Date.to_string(r.certificate_expiry),
                "days": r.days_to_expiry,
            } for r in expiring.sorted("days_to_expiry")[:12]],
            "by_category": sorted(by_cat.items(), key=lambda x: -x[1]),
            "top_learners": top_learners,
        }

    # ---------- Engagement ----------
    @api.model
    def engagement_data(self):
        today = fields.Date.today()
        Rec = self.env["mn.hr.recognition"].sudo()
        Sug = self.env["mn.hr.suggestion"].sudo()
        Ref = self.env["mn.hr.referral"].sudo()
        Exit = self.env["mn.hr.exit.interview"].sudo()
        F360 = self.env["mn.hr.feedback360"].sudo()
        Okr = self.env["mn.hr.okr"].sudo()

        recs = Rec.search([("award_date", ">=", today - timedelta(days=90))])
        rec_by_type = {}
        for r in recs:
            k = dict(Rec._fields["award_type"].selection).get(r.award_type, r.award_type)
            rec_by_type[k] = rec_by_type.get(k, 0) + 1

        exits = Exit.search([("interview_date", ">=", today - timedelta(days=365))])
        exit_reasons = {}
        for e in exits:
            k = dict(Exit._fields["leaving_reason"].selection).get(e.leaving_reason, e.leaving_reason)
            exit_reasons[k] = exit_reasons.get(k, 0) + 1
        # eNPS = %promoters - %detractors  (out of 10)
        nps_scores = exits.mapped("recommend_score")
        promoters = sum(1 for s in nps_scores if s >= 9)
        detractors = sum(1 for s in nps_scores if s <= 6)
        enps = round((promoters - detractors) / max(1, len(nps_scores)) * 100) if nps_scores else 0

        # Top recognised employees
        top_rec = {}
        for r in recs:
            top_rec[r.employee_id.name] = top_rec.get(r.employee_id.name, 0) + 1
        top_rec_list = sorted(top_rec.items(), key=lambda x: -x[1])[:6]

        # Referrals stats
        ref_all = Ref.search([])
        ref_hired = Ref.search([("state", "=", "hired")])

        return {
            "kpis": {
                "recognitions_90d": len(recs),
                "suggestions_open": len(Sug.search([("state", "in", ("new", "reviewing"))])),
                "suggestions_implemented": len(Sug.search([("state", "=", "implemented")])),
                "active_360": len(F360.search([("state", "=", "open")])),
                "active_okrs": len(Okr.search([("state", "=", "active")])),
                "avg_okr_progress": round(
                    sum(Okr.search([("state", "=", "active")]).mapped("progress_pct") or [0]) /
                    max(1, len(Okr.search([("state", "=", "active")]))), 1),
                "exits_12m": len(exits),
                "enps": enps,
                "referrals": len(ref_all),
                "referrals_hired": len(ref_hired),
                "referral_conv_pct": round(len(ref_hired) / max(1, len(ref_all)) * 100, 1),
            },
            "recognitions_by_type": sorted(rec_by_type.items(), key=lambda x: -x[1]),
            "exit_reasons": sorted(exit_reasons.items(), key=lambda x: -x[1]),
            "top_recognised": top_rec_list,
        }
