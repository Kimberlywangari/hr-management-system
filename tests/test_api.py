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


# --- new tests: withdraw, reversible decisions, overlap check, payroll lock ---

def test_withdraw_pending_request_no_balance_effect(client):
    emp = _create_employee(client, name="Pending Withdrawer")
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=12)).isoformat()
    resp = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start, "end_date": end})
    leave_id = resp.get_json()["id"]

    withdraw_resp = client.post(f"/api/leave/{leave_id}/withdraw")
    assert withdraw_resp.status_code == 200
    assert withdraw_resp.get_json()["status"] == "withdrawn"

    balance = client.get(f"/api/leave/balances/{emp['id']}").get_json()
    assert balance["remaining_days"] == 21


def test_withdraw_approved_request_reverses_balance(client):
    emp = _create_employee(client, name="Approved Withdrawer")
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=14)).isoformat()  # 5 days
    resp = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start, "end_date": end})
    leave_id = resp.get_json()["id"]
    client.post(f"/api/leave/{leave_id}/approve")

    balance_after_approval = client.get(f"/api/leave/balances/{emp['id']}").get_json()
    assert balance_after_approval["remaining_days"] == 16  # 21 - 5

    withdraw_resp = client.post(f"/api/leave/{leave_id}/withdraw")
    assert withdraw_resp.status_code == 200
    assert withdraw_resp.get_json()["status"] == "withdrawn"

    balance_after_withdraw = client.get(f"/api/leave/balances/{emp['id']}").get_json()
    assert balance_after_withdraw["remaining_days"] == 21


def test_reject_after_approval_reverses_balance(client):
    emp = _create_employee(client, name="Flip To Rejected")
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=13)).isoformat()  # 4 days
    resp = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start, "end_date": end})
    leave_id = resp.get_json()["id"]
    client.post(f"/api/leave/{leave_id}/approve")

    reject_resp = client.post(f"/api/leave/{leave_id}/reject")
    assert reject_resp.status_code == 200
    assert reject_resp.get_json()["status"] == "rejected"

    balance = client.get(f"/api/leave/balances/{emp['id']}").get_json()
    assert balance["remaining_days"] == 21


def test_approve_after_rejection_consumes_balance(client):
    emp = _create_employee(client, name="Flip To Approved")
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=12)).isoformat()  # 3 days
    resp = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start, "end_date": end})
    leave_id = resp.get_json()["id"]
    client.post(f"/api/leave/{leave_id}/reject")

    approve_resp = client.post(f"/api/leave/{leave_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.get_json()["status"] == "approved"

    balance = client.get(f"/api/leave/balances/{emp['id']}").get_json()
    assert balance["remaining_days"] == 18  # 21 - 3


def test_cannot_act_on_withdrawn_request(client):
    emp = _create_employee(client, name="Dead End")
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=11)).isoformat()
    resp = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start, "end_date": end})
    leave_id = resp.get_json()["id"]
    client.post(f"/api/leave/{leave_id}/withdraw")

    approve_resp = client.post(f"/api/leave/{leave_id}/approve")
    assert approve_resp.status_code == 400


def test_overlapping_leave_request_rejected(client):
    emp = _create_employee(client, name="Overlap Person")
    start1 = (date.today() + timedelta(days=10)).isoformat()
    end1 = (date.today() + timedelta(days=15)).isoformat()
    client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start1, "end_date": end1})

    start2 = (date.today() + timedelta(days=13)).isoformat()
    end2 = (date.today() + timedelta(days=18)).isoformat()
    resp2 = client.post("/api/leave", json={"employee_id": emp["id"], "start_date": start2, "end_date": end2})
    assert resp2.status_code == 400


def test_payroll_lock_blocks_reject_of_approved_leave(client):
    emp = _create_employee(client, name="Locked Person", start_date="2020-01-01")
    resp = client.post("/api/leave", json={
        "employee_id": emp["id"], "start_date": "2026-09-05", "end_date": "2026-09-07",
    })
    leave_id = resp.get_json()["id"]
    client.post(f"/api/leave/{leave_id}/approve")

    payroll_resp = client.post("/api/payroll/generate", json={"year": 2026, "month": 9})
    assert payroll_resp.status_code == 201

    reject_resp = client.post(f"/api/leave/{leave_id}/reject")
    assert reject_resp.status_code == 400
    assert "payroll" in reject_resp.get_json()["error"].lower()


def test_payroll_lock_blocks_approving_pending_leave_in_locked_month(client):
    emp = _create_employee(client, name="Late Submitter", start_date="2020-01-01")
    client.post("/api/payroll/generate", json={"year": 2026, "month": 10})

    resp = client.post("/api/leave", json={
        "employee_id": emp["id"], "start_date": "2026-10-05", "end_date": "2026-10-06",
    })
    assert resp.status_code == 201  # submission itself is still allowed

    leave_id = resp.get_json()["id"]
    approve_resp = client.post(f"/api/leave/{leave_id}/approve")
    assert approve_resp.status_code == 400
    assert "payroll" in approve_resp.get_json()["error"].lower()


def test_list_payroll_runs(client):
    _create_employee(client, name="Someone For Runs List")
    client.post("/api/payroll/generate", json={"year": 2026, "month": 11})
    resp = client.get("/api/payroll")
    assert resp.status_code == 200
    periods = [(r["period_year"], r["period_month"]) for r in resp.get_json()]
    assert (2026, 11) in periods


def test_export_csv_for_generated_period(client):
    _create_employee(client, name="CSV Person", salary=80_000)
    client.post("/api/payroll/generate", json={"year": 2026, "month": 12})
    resp = client.get("/api/payroll/2026/12/export")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert b"CSV Person" in resp.data


def test_export_csv_missing_period_returns_404(client):
    resp = client.get("/api/payroll/2030/1/export")
    assert resp.status_code == 404


def test_get_all_balances_returns_active_employees_only(client):
    _create_employee(client, name="Balance Visible")
    inactive = _create_employee(client, name="Balance Hidden")
    client.post(f"/api/employees/{inactive['id']}/deactivate")

    resp = client.get("/api/leave/balances")
    names = [b["employee_name"] for b in resp.get_json()]
    assert "Balance Visible" in names
    assert "Balance Hidden" not in names