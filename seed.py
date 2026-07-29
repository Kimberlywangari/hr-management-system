"""Run with: python seed.py
Populates a few teams, employees, leave requests, leave balances, and one
generated payroll period. Run this AFTER the server has started at least
once (so tables exist), or it will create tables itself via create_app().
"""
from datetime import date, timedelta
from app import create_app, db
from app.models import Team, Employee, LeaveRequest, LeaveBalance, PayrollRun, Payslip
from app.payroll_calc import calculate_payslip
from app.routes.payroll import _unpaid_leave_days_for_period

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    eng = Team(name="Engineering")
    ops = Team(name="Operations")
    db.session.add_all([eng, ops])
    db.session.commit()

    ceo = Employee(
        name="Kimberly Wangari", role="CEO", team_id=None, manager_id=None,
        start_date=date(2022, 1, 10), salary=250_000, employment_type="full_time",
    )
    db.session.add(ceo)
    db.session.commit()

    eng_lead = Employee(
        name="Brian Mutiso", role="Engineering Lead", team_id=eng.id, manager_id=ceo.id,
        start_date=date(2022, 3, 1), salary=180_000, employment_type="full_time",
    )
    db.session.add(eng_lead)
    db.session.commit()

    dev1 = Employee(
        name="Cynthia Wafula", role="Senior Software Engineer", team_id=eng.id, manager_id=eng_lead.id,
        start_date=date(2023, 6, 15), salary=120_000, employment_type="full_time",
    )
    dev2 = Employee(
        name="David Kiptoo", role="Junior Software Engineer", team_id=eng.id, manager_id=eng_lead.id,
        start_date=date(2024, 2, 1), salary=50_000, employment_type="full_time",
    )
    ops_lead = Employee(
        name="Esther Nyambura", role="Ops Lead", team_id=ops.id, manager_id=ceo.id,
        start_date=date(2022, 5, 20), salary=150_000, employment_type="full_time",
    )
    ops_staff = Employee(
        name="Felix Omondi", role="Ops Associate", team_id=ops.id, manager_id=None,
        start_date=date(2026, 7, 15), salary=60_000, employment_type="contract",
    )
    db.session.add_all([dev1, dev2, ops_lead, ops_staff])
    db.session.commit()
    ops_staff.manager_id = ops_lead.id
    db.session.commit()

    today = date.today()
    for emp in [ceo, eng_lead, dev1, dev2, ops_lead, ops_staff]:
        db.session.add(LeaveBalance(employee_id=emp.id, year=today.year, allocated_days=21, used_days=0))
    db.session.commit()

    lr1 = LeaveRequest(
        employee_id=dev1.id, start_date=date(2026, 7, 10), end_date=date(2026, 7, 14),
        days_requested=5, status="approved", is_unpaid=False, unpaid_days=0,
        reason="Family event", decided_by="Brian Mutiso",
    )
    lr2 = LeaveRequest(
        employee_id=dev2.id, start_date=today + timedelta(days=1), end_date=today + timedelta(days=3),
        days_requested=3, status="pending", flags="short_notice", reason="Personal",
    )
    lr3 = LeaveRequest(
        employee_id=ops_staff.id, start_date=date(2026, 7, 20), end_date=date(2026, 7, 31),
        days_requested=12, status="approved", is_unpaid=True, unpaid_days=3,
        reason="Extended leave beyond balance", decided_by="Esther Nyambura",
    )
    db.session.add_all([lr1, lr2, lr3])
    db.session.commit()

    bal_dev1 = LeaveBalance.query.filter_by(employee_id=dev1.id, year=today.year).first()
    bal_dev1.used_days = 5
    bal_ops = LeaveBalance.query.filter_by(employee_id=ops_staff.id, year=today.year).first()
    bal_ops.used_days = 9
    db.session.commit()

    print("Seed data created: 2 teams, 6 employees, 3 leave requests, 6 leave balances.")

    # Generate one payroll period, using the exact same tested logic the API
    # route uses, so seeded payslips are guaranteed correct rather than
    # hand-typed guesses that could drift from the real calculation.
    payroll_year, payroll_month = 2026, 7
    run = PayrollRun(period_month=payroll_month, period_year=payroll_year)
    db.session.add(run)
    db.session.flush()

    for emp in Employee.query.filter_by(active=True).all():
        unpaid_days = _unpaid_leave_days_for_period(emp.id, payroll_year, payroll_month)
        calc = calculate_payslip(
            monthly_salary=emp.salary,
            year=payroll_year,
            month=payroll_month,
            employee_start_date=emp.start_date,
            unpaid_leave_days=unpaid_days,
        )
        db.session.add(Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            working_days=calc["working_days"],
            unpaid_leave_days=calc["unpaid_leave_days"],
            gross_pay=calc["gross_pay"],
            tax_deducted=calc["tax_deducted"],
            social_security_deducted=calc["social_security_deducted"],
            net_pay=calc["net_pay"],
        ))
    db.session.commit()

    print(f"Payroll generated for {payroll_year}-{payroll_month:02d}: {len(run.payslips)} payslips.")