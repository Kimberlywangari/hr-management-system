from datetime import datetime, date, timedelta
from app.rules import (
    check_notice,
    check_team_coverage,
    check_stale,
    evaluate_leave_request,
    MIN_NOTICE_DAYS,
)


def test_short_notice_flagged():
    assert check_notice(datetime(2026, 7, 26), date(2026, 7, 27)) is True


def test_sufficient_notice_not_flagged():
    assert check_notice(datetime(2026, 7, 20), date(2026, 7, 27)) is False


def test_notice_exactly_at_threshold_not_flagged():
    request_date = datetime(2026, 7, 20)
    leave_start = date(2026, 7, 20) + timedelta(days=MIN_NOTICE_DAYS)
    assert check_notice(request_date, leave_start) is False


def test_team_coverage_flag_triggers_over_threshold():
    assert check_team_coverage(team_size=5, concurrent_leave_count=2) is True


def test_team_coverage_flag_does_not_trigger_under_threshold():
    assert check_team_coverage(team_size=10, concurrent_leave_count=1) is False


def test_team_coverage_handles_zero_team_size():
    assert check_team_coverage(team_size=0, concurrent_leave_count=0) is False


def test_stale_request_flagged_after_48_hours():
    old_request = datetime.utcnow() - timedelta(hours=49)
    assert check_stale(old_request) is True


def test_recent_request_not_stale():
    recent_request = datetime.utcnow() - timedelta(hours=2)
    assert check_stale(recent_request) is False


def test_evaluate_flags_exceeds_balance_as_unpaid():
    result = evaluate_leave_request(
        request_date=datetime(2026, 7, 1), leave_start=date(2026, 7, 15),
        team_size=10, concurrent_leave_count=0, remaining_balance=5, days_requested=8,
    )
    assert result["is_unpaid"] is True
    assert result["unpaid_days"] == 3
    assert "exceeds_balance" in result["flags"]


def test_evaluate_within_balance_is_paid():
    result = evaluate_leave_request(
        request_date=datetime(2026, 7, 1), leave_start=date(2026, 7, 15),
        team_size=10, concurrent_leave_count=0, remaining_balance=10, days_requested=5,
    )
    assert result["is_unpaid"] is False
    assert result["unpaid_days"] == 0
    assert "exceeds_balance" not in result["flags"]


def test_evaluate_negative_remaining_balance_all_unpaid():
    result = evaluate_leave_request(
        request_date=datetime(2026, 7, 1), leave_start=date(2026, 7, 15),
        team_size=10, concurrent_leave_count=0, remaining_balance=-2, days_requested=3,
    )
    assert result["unpaid_days"] == 3
    assert result["is_unpaid"] is True