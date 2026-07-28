from datetime import datetime
from flask import Blueprint, request, jsonify
from app import db
from app.models import Employee, Team

employees_bp = Blueprint("employees", __name__)


@employees_bp.get("")
def list_employees():
    active_only = request.args.get("active", "true").lower() == "true"
    query = Employee.query
    if active_only:
        query = query.filter_by(active=True)
    employees = query.all()
    return jsonify([e.to_dict() for e in employees])


@employees_bp.post("")
def create_employee():
    data = request.get_json()
    try:
        emp = Employee(
            name=data["name"],
            role=data["role"],
            team_id=data.get("team_id"),
            manager_id=data.get("manager_id"),
            start_date=datetime.strptime(data["start_date"], "%Y-%m-%d").date(),
            salary=float(data["salary"]),
            employment_type=data.get("employment_type", "full_time"),
        )
        db.session.add(emp)
        db.session.commit()
        return jsonify(emp.to_dict()), 201
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400


@employees_bp.patch("/<int:employee_id>")
def update_employee(employee_id):
    emp = db.get_or_404(Employee, employee_id)
    data = request.get_json()
    for field in ["name", "role", "team_id", "manager_id", "salary", "employment_type"]:
        if field in data:
            setattr(emp, field, data[field])
    db.session.commit()
    return jsonify(emp.to_dict())


@employees_bp.post("/<int:employee_id>/deactivate")
def deactivate_employee(employee_id):
    emp = db.get_or_404(Employee, employee_id)
    emp.active = False
    db.session.commit()
    return jsonify(emp.to_dict())


@employees_bp.get("/org-chart")
def org_chart():
    employees = Employee.query.filter_by(active=True).all()
    by_manager = {}
    for e in employees:
        by_manager.setdefault(e.manager_id, []).append(e.to_dict())
    return jsonify(by_manager)


@employees_bp.get("/teams")
def list_teams():
    teams = Team.query.all()
    return jsonify([{"id": t.id, "name": t.name} for t in teams])


@employees_bp.post("/teams")
def create_team():
    data = request.get_json()
    team = Team(name=data["name"])
    db.session.add(team)
    db.session.commit()
    return jsonify({"id": team.id, "name": team.name}), 201