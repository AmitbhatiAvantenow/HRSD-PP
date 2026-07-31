def migrate(cr, version):
    """HRA/DA/Travel/Meal/Medical/Other salary rule categories were seeded
    under noupdate="1" without a parent_id, so a later XML fix that tried to
    roll them up under the Allowance (ALW) category was silently ignored by
    the ORM on every module upgrade. Without the roll-up, categories.ALW
    excludes HRA and Medical, so the "Project and Special Allowance"
    balancing rule (which subtracts categories.ALW from the pro-rated gross
    target) overstates itself by exactly the missing HRA/Medical amount.
    Fix already-installed databases directly; fresh installs get the
    correct parent_id from data/hr_payroll_community_data.xml."""
    cr.execute("""
        SELECT alw.res_id
        FROM ir_model_data alw
        WHERE alw.module = 'hr_payroll_community' AND alw.name = 'ALW'
    """)
    row = cr.fetchone()
    if not row:
        return
    alw_id = row[0]
    cr.execute("""
        UPDATE hr_salary_rule_category cat
        SET parent_id = %s
        FROM ir_model_data d
        WHERE d.model = 'hr.salary.rule.category'
          AND d.module = 'hr_payroll_community'
          AND d.name IN ('HRA', 'DA', 'Travel', 'Meal', 'Medical', 'Other')
          AND cat.id = d.res_id
          AND cat.parent_id IS NULL
    """, (alw_id,))
