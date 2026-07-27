from datetime import date, timedelta


def _create_employee(client, **overrides):
    payload = {
        "name": "Test Employee", "role": "Engineer", "start_date": "2024-01-01",
        "salary": 100_000, "employment_type": "full_time",
    }
    payload.update(overrides)
    resp = client.post("/api/employees", json=payload)
    assert resp.status_code == 201
    return resp.get_json()


def test_create_and_list_employee(client):
    _create_employee(client, name="Jane Doe")
    resp = client.get("/api/employees")
    names = [e["name"] for e in resp.get_json()]
    assert "Jane Doe" in names


def test_deactivate_employee_hides_from_default_list(client):
    emp = _create_employee(client, name="Leaving Soon")
    client.post(f"/api/employees/{emp['id']}/deactivate")
    resp = client.get("/api/employees")
    assert "Leaving Soon" not in [e["name"] for e in resp.get_json()]
    resp_all = client.get("/api/employees?active=false")
    assert "Leaving Soon" in [e["name"] for e in resp_all.get_json()]


def test_leave_request_over_balance_marked_unpaid_on_approval(client):
    emp = _create_employee(client, name="Over Balance Person")
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=35)).isoformat()  # 26 days > 21 balance
    resp = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start, "end_date": end})
    leave = resp.get_json()
    approve_resp = client.post(f"/api/leave/{leave['id']}/approve", json={"decided_by": "Manager X"})
    approved = approve_resp.get_json()
    assert approved["status"] == "approved"
    assert approved["is_unpaid"] is True
    assert approved["unpaid_days"] > 0


def test_short_notice_request_is_flagged(client):
    emp = _create_employee(client, name="Rushed Person")
    start = (date.today() + timedelta(days=1)).isoformat()
    end = (date.today() + timedelta(days=2)).isoformat()
    resp = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start, "end_date": end})
    assert "short_notice" in resp.get_json()["flags"]


def test_cannot_approve_already_decided_request(client):
    emp = _create_employee(client, name="Double Approve")
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=11)).isoformat()
    resp = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start, "end_date": end})
    leave_id = resp.get_json()["id"]
    client.post(f"/api/leave/{leave_id}/approve")
    second = client.post(f"/api/leave/{leave_id}/approve")
    assert second.status_code == 400


def test_generate_payroll_creates_payslip_per_active_employee(client):
    _create_employee(client, name="Payroll Person One", salary=100_000)
    _create_employee(client, name="Payroll Person Two", salary=50_000)
    inactive = _create_employee(client, name="Inactive Person", salary=80_000)
    client.post(f"/api/employees/{inactive['id']}/deactivate")

    resp = client.post("/api/payroll/generate", json={"year": 2026, "month": 7})
    assert resp.status_code == 201
    names = [p["employee_name"] for p in resp.get_json()["payslips"]]
    assert "Payroll Person One" in names
    assert "Payroll Person Two" in names
    assert "Inactive Person" not in names


def test_cannot_generate_payroll_twice_for_same_period(client):
    _create_employee(client, name="Someone")
    client.post("/api/payroll/generate", json={"year": 2026, "month": 8})
    second = client.post("/api/payroll/generate", json={"year": 2026, "month": 8})
    assert second.status_code == 400


def test_mid_month_joiner_payslip_prorated(client):
    _create_employee(client, name="Mid Month Joiner", start_date="2026-09-15", salary=90_000)
    resp = client.post("/api/payroll/generate", json={"year": 2026, "month": 9})
    payslip = next(p for p in resp.get_json()["payslips"] if p["employee_name"] == "Mid Month Joiner")
    assert 0 < payslip["gross_pay"] < 90_000
    assert payslip["unpaid_leave_days"] > 0