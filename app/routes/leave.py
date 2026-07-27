from datetime import datetime, date
from flask import Blueprint, request, jsonify
from app import db
from app.models import LeaveRequest, LeaveBalance, Employee
from app.rules import evaluate_leave_request, check_stale

leave_bp = Blueprint("leave", __name__)


def _get_or_create_balance(employee_id, year):
    bal = LeaveBalance.query.filter_by(employee_id=employee_id, year=year).first()
    if not bal:
        bal = LeaveBalance(employee_id=employee_id, year=year, allocated_days=21, used_days=0)
        db.session.add(bal)
        db.session.commit()
    return bal


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
    if leave_req.status != "pending":
        return jsonify({"error": "Request already decided"}), 400

    balance = _get_or_create_balance(leave_req.employee_id, leave_req.start_date.year)
    paid_days = min(leave_req.days_requested, balance.remaining_days)
    paid_days = max(0.0, paid_days)
    unpaid_days = leave_req.days_requested - paid_days

    balance.used_days += paid_days
    leave_req.is_unpaid = unpaid_days > 0
    leave_req.unpaid_days = unpaid_days
    leave_req.status = "approved"
    leave_req.decided_at = datetime.utcnow()
    body = request.get_json(silent=True) or {}
    leave_req.decided_by = body.get("decided_by", "manager")
    db.session.commit()
    return jsonify(leave_req.to_dict())


@leave_bp.post("/<int:request_id>/reject")
def reject_leave(request_id):
    leave_req = LeaveRequest.query.get_or_404(request_id)
    if leave_req.status != "pending":
        return jsonify({"error": "Request already decided"}), 400
    leave_req.status = "rejected"
    leave_req.decided_at = datetime.utcnow()
    body = request.get_json(silent=True) or {}
    leave_req.decided_by = body.get("decided_by", "manager")
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