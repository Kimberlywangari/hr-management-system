from datetime import datetime, timezone
from app import db


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    employees = db.relationship("Employee", back_populates="team")


class Employee(db.Model):
    __tablename__ = "employees"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    salary = db.Column(db.Float, nullable=False)
    employment_type = db.Column(db.String(50), nullable=False, default="full_time")
    active = db.Column(db.Boolean, nullable=False, default=True)

    team = db.relationship("Team", back_populates="employees")
    manager = db.relationship("Employee", remote_side=[id], backref="reports")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "team_id": self.team_id,
            "team_name": self.team.name if self.team else None,
            "manager_id": self.manager_id,
            "manager_name": self.manager.name if self.manager else None,
            "start_date": self.start_date.isoformat(),
            "salary": self.salary,
            "employment_type": self.employment_type,
            "active": self.active,
        }


class LeaveBalance(db.Model):
    __tablename__ = "leave_balances"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    allocated_days = db.Column(db.Float, nullable=False, default=21)
    used_days = db.Column(db.Float, nullable=False, default=0)

    __table_args__ = (db.UniqueConstraint("employee_id", "year", name="uq_emp_year"),)

    @property
    def remaining_days(self):
        return self.allocated_days - self.used_days


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    is_unpaid = db.Column(db.Boolean, nullable=False, default=False)
    unpaid_days = db.Column(db.Float, nullable=False, default=0)
    flags = db.Column(db.String(500), nullable=True)
    reason = db.Column(db.String(500), nullable=True)
    requested_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    decided_at = db.Column(db.DateTime, nullable=True)
    decided_by = db.Column(db.String(150), nullable=True)

    employee = db.relationship("Employee")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else None,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days_requested": self.days_requested,
            "status": self.status,
            "is_unpaid": self.is_unpaid,
            "unpaid_days": self.unpaid_days,
            "flags": self.flags.split(",") if self.flags else [],
            "reason": self.reason,
            "requested_at": self.requested_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "decided_by": self.decided_by,
        }


class PayrollRun(db.Model):
    __tablename__ = "payroll_runs"
    id = db.Column(db.Integer, primary_key=True)
    period_month = db.Column(db.Integer, nullable=False)
    period_year = db.Column(db.Integer, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("period_month", "period_year", name="uq_period"),)

    payslips = db.relationship("Payslip", back_populates="payroll_run")


class Payslip(db.Model):
    __tablename__ = "payslips"
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey("payroll_runs.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    working_days = db.Column(db.Integer, nullable=False)
    unpaid_leave_days = db.Column(db.Float, nullable=False, default=0)
    gross_pay = db.Column(db.Float, nullable=False)
    tax_deducted = db.Column(db.Float, nullable=False)
    social_security_deducted = db.Column(db.Float, nullable=False)
    net_pay = db.Column(db.Float, nullable=False)

    payroll_run = db.relationship("PayrollRun", back_populates="payslips")
    employee = db.relationship("Employee")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else None,
            "working_days": self.working_days,
            "unpaid_leave_days": self.unpaid_leave_days,
            "gross_pay": round(self.gross_pay, 2),
            "tax_deducted": round(self.tax_deducted, 2),
            "social_security_deducted": round(self.social_security_deducted, 2),
            "net_pay": round(self.net_pay, 2),
        }