"""
Leave request business rules.

PROBLEMS IDENTIFIED (spreadsheets/WhatsApp don't catch these):
1. Short-notice requests slip through with no visibility -> flagged, not auto-rejected,
   so a manager makes the final call but can't miss it.
2. Team under-coverage: multiple overlapping approvals can quietly leave a team short-staffed.
   -> flagged if approving this request would push same-team concurrent leave above a threshold.
3. Requests sitting unanswered -> anything pending longer than STALE_HOURS is flagged as
   "stale" so it surfaces on the dashboard instead of rotting silently.
4. Balance overrun -> if a request exceeds the employee's remaining balance, it isn't
   blocked outright (life happens), but it's marked as (partially) unpaid, which feeds
   directly into payroll pro-ration.
5. Duplicate/overlapping requests for the same employee silently double-count
   balance usage if both get approved -> this is a hard validation error at
   submission time, not a soft flag, since it's a data-integrity problem rather
   than a judgment call a manager should weigh in on.

These are FLAGS, not hard blocks (except balance, which determines paid vs unpaid
rather than blocking). The manager retains final approve/reject authority; the
system's job is to surface risk, not make the decision for them.
"""

from datetime import datetime, timedelta, timezone

MIN_NOTICE_DAYS = 3
TEAM_COVERAGE_THRESHOLD = 0.4  # flag if >40% of team is out concurrently
STALE_HOURS = 48


def check_notice(request_date: datetime, leave_start) -> bool:
    """True if request was made with less than MIN_NOTICE_DAYS notice."""
    notice_days = (leave_start - request_date.date()).days
    return notice_days < MIN_NOTICE_DAYS


def check_team_coverage(team_size: int, concurrent_leave_count: int) -> bool:
    """True if approving would push concurrent team leave above threshold."""
    if team_size == 0:
        return False
    return (concurrent_leave_count + 1) / team_size > TEAM_COVERAGE_THRESHOLD


def check_stale(requested_at: datetime, now: datetime = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return (now - requested_at) > timedelta(hours=STALE_HOURS)


def evaluate_leave_request(
    request_date: datetime,
    leave_start,
    team_size: int,
    concurrent_leave_count: int,
    remaining_balance: float,
    days_requested: float,
) -> dict:
    """
    Returns dict: {flags: [...], is_unpaid: bool, unpaid_days: float}
    """
    flags = []

    if check_notice(request_date, leave_start):
        flags.append("short_notice")

    if check_team_coverage(team_size, concurrent_leave_count):
        flags.append("team_under_coverage")

    unpaid_days = 0.0
    if days_requested > remaining_balance:
        unpaid_days = days_requested - max(0.0, remaining_balance)
        flags.append("exceeds_balance")

    return {
        "flags": flags,
        "is_unpaid": unpaid_days > 0,
        "unpaid_days": unpaid_days,
    }
def check_overlap(existing_requests, new_start, new_end):
    """True if [new_start, new_end] overlaps the date range of any request
    in existing_requests. Caller is responsible for pre-filtering existing_requests
    to the same employee and to pending/approved status — this function only
    does the date-range comparison, so it stays free of any DB dependency and
    is easy to unit test in isolation."""
    for r in existing_requests:
        if r.start_date <= new_end and r.end_date >= new_start:
            return True
    return False