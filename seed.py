"""Run with: python seed.py
Populates a few teams, employees, leave requests, and leave balances.
Run this AFTER the server has started at least once (so tables exist),
or it will create tables itself via create_app().
"""
from datetime import date, timedelta
from app import create_app, db
from app.models import Team, Employee, LeaveRequest, LeaveBalance

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
    print('Generate payroll via: POST /api/payroll/generate {"year":2026,"month":7}')