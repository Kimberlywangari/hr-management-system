from datetime import date
from app.payroll_calc import (
    calculate_payslip,
    calculate_tax,
    calculate_social_security,
    working_days_in_month,
)


def test_working_days_excludes_sundays():
    wd = working_days_in_month(2026, 7)
    assert wd == 27  # 31 days in July 2026, 4 Sundays


def test_full_month_no_leave_full_time_employee():
    result = calculate_payslip(120_000, 2026, 7, date(2020, 1, 1), unpaid_leave_days=0)
    assert result["unpaid_leave_days"] == 0
    assert round(result["gross_pay"], 2) == 120_000.0
    assert result["net_pay"] < result["gross_pay"]
    assert result["net_pay"] > 0


def test_mid_month_joiner_prorates_correctly():
    result = calculate_payslip(120_000, 2026, 7, date(2026, 7, 15), unpaid_leave_days=0)
    total_wd = working_days_in_month(2026, 7)
    assert result["working_days"] == total_wd
    assert result["unpaid_leave_days"] > 0
    assert 0 < result["gross_pay"] < 120_000


def test_employee_joins_after_period_gets_zero_pay():
    result = calculate_payslip(100_000, 2026, 6, date(2026, 7, 1), unpaid_leave_days=0)
    assert result["gross_pay"] == 0
    assert result["net_pay"] == 0


def test_unpaid_leave_reduces_gross_pay():
    full = calculate_payslip(120_000, 2026, 7, date(2020, 1, 1), unpaid_leave_days=0)
    with_leave = calculate_payslip(120_000, 2026, 7, date(2020, 1, 1), unpaid_leave_days=5)
    assert with_leave["gross_pay"] < full["gross_pay"]
    assert with_leave["net_pay"] < full["net_pay"]


def test_zero_deduction_case_low_salary():
    result = calculate_payslip(5_000, 2026, 7, date(2020, 1, 1), unpaid_leave_days=0)
    assert result["tax_deducted"] >= 0
    assert 0 <= result["net_pay"] <= result["gross_pay"]


def test_salary_at_zero_no_negative_net():
    result = calculate_payslip(0, 2026, 7, date(2020, 1, 1), unpaid_leave_days=0)
    assert result["gross_pay"] == 0
    assert result["tax_deducted"] == 0
    assert result["net_pay"] == 0


def test_tax_bracket_boundaries():
    assert calculate_tax(24_000) == 2_400.0
    tax = calculate_tax(24_001)
    assert round(tax, 2) == round(2_400 + 0.25 * 1, 2)
    tax_high = calculate_tax(50_000)
    expected = (24_000 * 0.10) + ((32_333 - 24_000) * 0.25) + ((50_000 - 32_333) * 0.30)
    assert round(tax_high, 2) == round(expected, 2)


def test_tax_negative_or_zero_income_returns_zero():
    assert calculate_tax(0) == 0.0
    assert calculate_tax(-500) == 0.0


def test_social_security_cap_applies():
    assert calculate_social_security(1_000_000) == 2_160.0


def test_social_security_below_cap_is_proportional():
    assert round(calculate_social_security(10_000), 2) == 600.0