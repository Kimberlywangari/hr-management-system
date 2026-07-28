from datetime import datetime, date
from flask import Blueprint, request, jsonify
from app import db
from app.models import LeaveRequest, LeaveBalance, Employee, PayrollRun
from app.rules import evaluate_leave_request, check_stale, check_overlap

leave_bp = Blueprint("leave", __name__)


def _get_or_create_balance(employee_id, year):
    bal = LeaveBalance.query.filter_by(employee_id=employee_id, year=year).first()
    if not bal:
        bal = LeaveBalance(employee_id=employee_id, year=year, allocated_days=21, used_days=0)
        db.session.add(bal)
        db.session.commit()
    return bal


def _months_between(start_date, end_date):
    """List of (year, month) tuples spanned by a date range, inclusive."""
    months = []
    year, month = start_date.year, start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        months.append((year, month))
        month = 1 if month == 12 else month + 1
        if month == 1 and (year, 12) in [(year, m) for m in [months[-1][1]]] and months[-1][1] == 12:
            year += 1
    return months


def _find_locked_period(start_date, end_date):
    """Return the first (year, month) in range with an existing payroll run,
    or None if none of the covered months are locked yet."""
    year, month = start_date.year, start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        if PayrollRun.query.filter_by(period_year=year, period_month=month).first():
            return (year, month)
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return None


def _apply_approval(leave_req, balance):
    """Consume balance for this request, marking unpaid days as needed."""
    paid_days = min(leave_req.days_requested, balance.remaining_days)
    paid_days = max(0.0, paid_days)
    unpaid_days = leave_req.days_requested - paid_days
    balance.used_days += paid_days
    leave_req.is_unpaid = unpaid_days > 0
    leave_req.unpaid_days = unpaid_days


def _reverse_approval(leave_req, balance):
    """Give back whatever balance this request's prior approval consumed."""
    paid_days_previously = leave_req.days_requested - leave_req.unpaid_days
    balance.used_days = max(0.0, balance.used_days - paid_days_previously)
    leave_req.is_unpaid = False
    leave_req.unpaid_days = 0


@leave_bp.get("")
def list_leave_requests():
    status = request.args.get("status")
    query = LeaveRequest.query
    if status:
        query = query.filter_by(status=status)
    requests_ = query.order_by(LeaveRequest.requested_at.desc()).all()
    result = []
    for r in requests_:
        d = r.to_dict()
        if r.status == "pending" and check_stale(r.requested_at):
            if "stale" not in d["flags"]:
                d["flags"].append("stale")
        result.append(d)
    return jsonify(result)


@leave_bp.post("")
def submit_leave_request():
    data = request.get_json()
    employee = Employee.query.get_or_404(data["employee_id"])
    start = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
    end = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
    days_requested = (end - start).days + 1
    if days_requested <= 0:
        return jsonify({"error": "end_date must be on/after start_date"}), 400

    existing = LeaveRequest.query.filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status.in_(["pending", "approved"]),
    ).all()
    if check_overlap(existing, start, end):
        return jsonify({
            "error": "This employee already has a pending or approved request overlapping these dates"
        }), 400

    balance = _get_or_create_balance(employee.id, start.year)

    team_size = Employee.query.filter_by(team_id=employee.team_id, active=True).count()
    concurrent = (
        LeaveRequest.query
        .join(Employee)
        .filter(
            Employee.team_id == employee.team_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
        .count()
    )

    evaluation = evaluate_leave_request(
        request_date=datetime.utcnow(),
        leave_start=start,
        team_size=team_size,
        concurrent_leave_count=concurrent,
        remaining_balance=balance.remaining_days,
        days_requested=days_requested,
    )

    leave_req = LeaveRequest(
        employee_id=employee.id,
        start_date=start,
        end_date=end,
        days_requested=days_requested,
        status="pending",
        is_unpaid=evaluation["is_unpaid"],
        flags=",".join(evaluation["flags"]) if evaluation["flags"] else None,
        reason=data.get("reason"),
    )
    db.session.add(leave_req)
    db.session.commit()
    return jsonify(leave_req.to_dict()), 201


@leave_bp.post("/<int:request_id>/approve")
def approve_leave(request_id):
    leave_req = LeaveRequest.query.get_or_404(request_id)
    if leave_req.status not in ("pending", "rejected"):
        return jsonify({"error": f"Cannot approve a request that is currently {leave_req.status}"}), 400

    locked = _find_locked_period(leave_req.start_date, leave_req.end_date)
    if locked:
        return jsonify({
            "error": f"Cannot modify — payroll for {locked[0]}-{locked[1]:02d} has already been generated"
        }), 400

    balance = _get_or_create_balance(leave_req.employee_id, leave_req.start_date.year)
    _apply_approval(leave_req, balance)
    leave_req.status = "approved"
    leave_req.decided_at = datetime.utcnow()
    body = request.get_json(silent=True) or {}
    leave_req.decided_by = body.get("decided_by", "manager")
    db.session.commit()
    return jsonify(leave_req.to_dict())


@leave_bp.post("/<int:request_id>/reject")
def reject_leave(request_id):
    leave_req = LeaveRequest.query.get_or_404(request_id)
    if leave_req.status not in ("pending", "approved"):
        return jsonify({"error": f"Cannot reject a request that is currently {leave_req.status}"}), 400

    if leave_req.status == "approved":
        locked = _find_locked_period(leave_req.start_date, leave_req.end_date)
        if locked:
            return jsonify({
                "error": f"Cannot modify — payroll for {locked[0]}-{locked[1]:02d} has already been generated"
            }), 400
        balance = _get_or_create_balance(leave_req.employee_id, leave_req.start_date.year)
        _reverse_approval(leave_req, balance)

    leave_req.status = "rejected"
    leave_req.decided_at = datetime.utcnow()
    body = request.get_json(silent=True) or {}
    leave_req.decided_by = body.get("decided_by", "manager")
    db.session.commit()
    return jsonify(leave_req.to_dict())


@leave_bp.post("/<int:request_id>/withdraw")
def withdraw_leave(request_id):
    leave_req = LeaveRequest.query.get_or_404(request_id)
    if leave_req.status not in ("pending", "approved"):
        return jsonify({"error": f"Cannot withdraw a request that is currently {leave_req.status}"}), 400

    if leave_req.status == "approved":
        locked = _find_locked_period(leave_req.start_date, leave_req.end_date)
        if locked:
            return jsonify({
                "error": f"Cannot modify — payroll for {locked[0]}-{locked[1]:02d} has already been generated"
            }), 400
        balance = _get_or_create_balance(leave_req.employee_id, leave_req.start_date.year)
        _reverse_approval(leave_req, balance)

    leave_req.status = "withdrawn"
    leave_req.decided_at = datetime.utcnow()
    body = request.get_json(silent=True) or {}
    leave_req.decided_by = body.get("decided_by", "employee")
    db.session.commit()
    return jsonify(leave_req.to_dict())


@leave_bp.get("/balances/<int:employee_id>")
def get_balance(employee_id):
    year = int(request.args.get("year", date.today().year))
    balance = _get_or_create_balance(employee_id, year)
    return jsonify({
        "employee_id": employee_id,
        "year": year,
        "allocated_days": balance.allocated_days,
        "used_days": balance.used_days,
        "remaining_days": balance.remaining_days,
    })


@leave_bp.get("/balances")
def get_all_balances():
    year = int(request.args.get("year", date.today().year))
    employees = Employee.query.filter_by(active=True).all()
    result = []
    for emp in employees:
        bal = _get_or_create_balance(emp.id, year)
        result.append({
            "employee_id": emp.id,
            "employee_name": emp.name,
            "year": year,
            "allocated_days": bal.allocated_days,
            "used_days": bal.used_days,
            "remaining_days": bal.remaining_days,
        })
    return jsonify(result)


@leave_bp.get("/who-is-out")
def who_is_out():
    today = date.today()
    active = (
        LeaveRequest.query
        .join(Employee)
        .filter(
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
        )
        .all()
    )
    return jsonify([r.to_dict() for r in active])