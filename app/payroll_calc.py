"""
Payroll calculation logic.

ASSUMPTIONS (documented here and in README):
- Working days in a month = all calendar days minus Sundays (simple 6-day work week).
  This is a deliberate simplification; a real system would use a holiday calendar.
- Gross pay is pro-rated by working days actually owed:
    gross_pay = (monthly_salary / working_days_in_month) * (working_days_in_month - unpaid_days)
  where unpaid_days accounts for both mid-month starts (days before start_date in that
  month are unpaid, since the employee wasn't employed yet) and approved unpaid leave.
- Tax is a marginal bracket scheme (each bracket taxed only on the income within it),
  applied to gross_pay (post pro-ration), not full monthly salary. This matters for
  mid-month joiners / heavy unpaid leave, who should be taxed on what they actually earned.
- Social security is a flat 6% of gross_pay, capped at KES 2,160/month (mirroring
  NSSF-style tiered caps without claiming to replicate any specific country's scheme).
- Net pay = gross_pay - tax - social_security. Floored at 0 as a safety check.
"""

import calendar
from datetime import date

TAX_BRACKETS = [
    (0, 24_000, 0.10),
    (24_000, 32_333, 0.25),
    (32_333, float("inf"), 0.30),
]

SOCIAL_SECURITY_RATE = 0.06
SOCIAL_SECURITY_CAP = 2_160.0


def working_days_in_month(year: int, month: int) -> int:
    """Calendar days minus Sundays. Simple documented assumption."""
    _, days_in_month = calendar.monthrange(year, month)
    count = 0
    for day in range(1, days_in_month + 1):
        if date(year, month, day).weekday() != 6:  # 6 = Sunday
            count += 1
    return count


def working_days_before(year: int, month: int, before_day: int) -> int:
    """Working days strictly before a given day-of-month (used for mid-month joiners)."""
    count = 0
    for day in range(1, before_day):
        if date(year, month, day).weekday() != 6:
            count += 1
    return count


def calculate_tax(taxable_amount: float) -> float:
    """Marginal bracket tax. Each bracket taxed only on income within it."""
    if taxable_amount <= 0:
        return 0.0
    tax = 0.0
    for lower, upper, rate in TAX_BRACKETS:
        if taxable_amount > lower:
            taxable_in_bracket = min(taxable_amount, upper) - lower
            tax += taxable_in_bracket * rate
        else:
            break
    return tax


def calculate_social_security(gross_pay: float) -> float:
    return min(gross_pay * SOCIAL_SECURITY_RATE, SOCIAL_SECURITY_CAP)


def calculate_payslip(
    monthly_salary: float,
    year: int,
    month: int,
    employee_start_date: date,
    unpaid_leave_days: float = 0.0,
) -> dict:
    """
    Returns dict with working_days, unpaid_leave_days (total, incl. pre-start days),
    gross_pay, tax_deducted, social_security_deducted, net_pay.
    """
    total_working_days = working_days_in_month(year, month)

    pre_start_unpaid = 0
    if employee_start_date.year == year and employee_start_date.month == month:
        pre_start_unpaid = working_days_before(year, month, employee_start_date.day)
    elif date(year, month, 1) < employee_start_date:
        pre_start_unpaid = total_working_days

    total_unpaid_days = min(total_working_days, pre_start_unpaid + unpaid_leave_days)

    if total_working_days == 0:
        gross_pay = 0.0
    else:
        paid_days = max(0, total_working_days - total_unpaid_days)
        gross_pay = (monthly_salary / total_working_days) * paid_days

    tax = calculate_tax(gross_pay)
    social_security = calculate_social_security(gross_pay)
    net_pay = max(0.0, gross_pay - tax - social_security)

    return {
        "working_days": total_working_days,
        "unpaid_leave_days": total_unpaid_days,
        "gross_pay": gross_pay,
        "tax_deducted": tax,
        "social_security_deducted": social_security,
        "net_pay": net_pay,
    }