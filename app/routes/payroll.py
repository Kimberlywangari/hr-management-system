import csv
import io
from datetime import date, timedelta
from flask import Blueprint, request, jsonify, Response
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
        proportion_in_period = overlap_days / r.days_requested if r.days_requested else 0
        total += r.unpaid_days * proportion_in_period
    return total


@payroll_bp.get("")
def list_payroll_runs():
    """All payroll runs ever generated, most recent first. This is how
    generated payslips stay accessible after the fact, since a period can
    only be generated once."""
    runs = PayrollRun.query.order_by(
        PayrollRun.period_year.desc(), PayrollRun.period_month.desc()
    ).all()
    return jsonify([
        {
            "payroll_run_id": r.id,
            "period_month": r.period_month,
            "period_year": r.period_year,
            "generated_at": r.generated_at.isoformat(),
            "employee_count": len(r.payslips),
        }
        for r in runs
    ])


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


@payroll_bp.get("/<int:year>/<int:month>/export")
def export_payroll_csv(year, month):
    run = PayrollRun.query.filter_by(period_year=year, period_month=month).first()
    if not run:
        return jsonify({"error": "No payroll run found for this period"}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Employee", "Working Days", "Unpaid Leave Days",
        "Gross Pay", "Tax Deducted", "Social Security", "Net Pay",
    ])
    for p in run.payslips:
        writer.writerow([
            p.employee.name, p.working_days, p.unpaid_leave_days,
            round(p.gross_pay, 2), round(p.tax_deducted, 2),
            round(p.social_security_deducted, 2), round(p.net_pay, 2),
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=payroll_{year}_{month}.csv"},
    )