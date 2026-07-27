from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from app import db
from app.models import PayrollRun, Payslip, Employee, LeaveRequest
from app.payroll_calc import calculate_payslip

payroll_bp = Blueprint("payroll", __name__)


def _unpaid_leave_days_for_period(employee_id, year, month):
    period_start = date(year, month, 1)
    if month == 12:
        period_end = date(year, 12, 31)
    else:
        next_month = date(year, month + 1, 1)
        period_end = next_month - timedelta(days=1)

    unpaid_requests = (
        LeaveRequest.query
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "approved",
            LeaveRequest.is_unpaid == True,  # noqa: E712
            LeaveRequest.start_date <= period_end,
            LeaveRequest.end_date >= period_start,
        )
        .all()
    )
    total = 0.0
    for r in unpaid_requests:
        overlap_start = max(r.start_date, period_start)
        overlap_end = min(r.end_date, period_end)
        overlap_days = (overlap_end - overlap_start).days + 1
        # Scale the request's unpaid_days by what fraction of the request falls
        # in this payroll period (handles a leave request spanning two months).
        proportion_in_period = overlap_days / r.days_requested if r.days_requested else 0
        total += r.unpaid_days * proportion_in_period
    return total


@payroll_bp.post("/generate")
def generate_payroll():
    data = request.get_json()
    year = int(data["year"])
    month = int(data["month"])

    existing = PayrollRun.query.filter_by(period_year=year, period_month=month).first()
    if existing:
        return jsonify({"error": "Payroll already generated for this period"}), 400

    run = PayrollRun(period_month=month, period_year=year)
    db.session.add(run)
    db.session.flush()

    employees = Employee.query.filter_by(active=True).all()
    payslips = []
    for emp in employees:
        unpaid_days = _unpaid_leave_days_for_period(emp.id, year, month)
        calc = calculate_payslip(
            monthly_salary=emp.salary,
            year=year,
            month=month,
            employee_start_date=emp.start_date,
            unpaid_leave_days=unpaid_days,
        )
        payslip = Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            working_days=calc["working_days"],
            unpaid_leave_days=calc["unpaid_leave_days"],
            gross_pay=calc["gross_pay"],
            tax_deducted=calc["tax_deducted"],
            social_security_deducted=calc["social_security_deducted"],
            net_pay=calc["net_pay"],
        )
        db.session.add(payslip)
        payslips.append(payslip)

    db.session.commit()
    return jsonify({
        "payroll_run_id": run.id,
        "period_month": month,
        "period_year": year,
        "payslips": [p.to_dict() for p in payslips],
    }), 201


@payroll_bp.get("/<int:year>/<int:month>")
def get_payroll(year, month):
    run = PayrollRun.query.filter_by(period_year=year, period_month=month).first()
    if not run:
        return jsonify({"payslips": [], "generated": False})
    return jsonify({
        "payroll_run_id": run.id,
        "generated": True,
        "generated_at": run.generated_at.isoformat(),
        "payslips": [p.to_dict() for p in run.payslips],
    })