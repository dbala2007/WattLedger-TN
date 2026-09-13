"""Tests for billing-cycle window calculation (app.domain.billing_cycles),
including the exact boundary day where one cycle ends and the next begins.
"""

from datetime import date

import pytest

from app.domain.billing_cycles import get_current_cycle_for_meter, get_cycle_containing
from app.models.meter import Meter


def test_target_on_reference_date_starts_that_cycle():
    start, end = get_cycle_containing(date(2026, 5, 10), 2, date(2026, 5, 10))
    assert start == date(2026, 5, 10)
    assert end == date(2026, 7, 9)


def test_target_in_middle_of_cycle():
    start, end = get_cycle_containing(date(2026, 5, 10), 2, date(2026, 6, 15))
    assert (start, end) == (date(2026, 5, 10), date(2026, 7, 9))


def test_target_on_last_day_of_cycle():
    start, end = get_cycle_containing(date(2026, 5, 10), 2, date(2026, 7, 9))
    assert (start, end) == (date(2026, 5, 10), date(2026, 7, 9))


def test_target_on_first_day_of_next_cycle():
    # One day after the previous test's end date must fall in the NEXT
    # cycle, not the same one - this is the billing-cycle boundary case.
    start, end = get_cycle_containing(date(2026, 5, 10), 2, date(2026, 7, 10))
    assert (start, end) == (date(2026, 7, 10), date(2026, 9, 9))


def test_target_several_cycles_ahead():
    start, end = get_cycle_containing(date(2026, 1, 1), 2, date(2026, 9, 4))
    # Cycles: Jan1-Feb28, Mar1-Apr30, May1-Jun30, Jul1-Aug31, Sep1-Oct31
    assert (start, end) == (date(2026, 9, 1), date(2026, 10, 31))


def test_target_before_reference_date_steps_backward():
    start, end = get_cycle_containing(date(2026, 5, 10), 2, date(2026, 2, 1))
    assert (start, end) == (date(2026, 1, 10), date(2026, 3, 9))


def test_month_end_day_clamping():
    # 31 Jan + 1 month clamps to the last valid day of February.
    start, end = get_cycle_containing(date(2026, 1, 31), 1, date(2026, 1, 31))
    assert start == date(2026, 1, 31)
    assert end == date(2026, 2, 27)  # day before clamped Feb 28 (2026 is not a leap year)


def test_get_current_cycle_for_meter_uses_meter_settings():
    meter = Meter(
        meter_number="EB-1",
        billing_cycle_reference_date=date(2026, 5, 10),
        cycle_length_months=2,
    )
    start, end = get_current_cycle_for_meter(meter, date(2026, 6, 1))
    assert (start, end) == (date(2026, 5, 10), date(2026, 7, 9))


def test_get_current_cycle_for_meter_without_reference_date_raises():
    meter = Meter(meter_number="EB-1")
    with pytest.raises(ValueError):
        get_current_cycle_for_meter(meter, date(2026, 6, 1))


def test_corrected_assessment_dates_override_fixed_interval_entirely():
    # The EB reader actually visited on 2026-05-14 and 2026-07-20 - a 67 day
    # cycle, not the fixed-interval 2-month math billing_cycle_reference_date
    # would otherwise produce. The correction must win regardless of as_of_date.
    meter = Meter(
        meter_number="EB-1",
        billing_cycle_reference_date=date(2026, 5, 10),
        cycle_length_months=2,
        last_assessment_date=date(2026, 5, 14),
        next_expected_assessment_date=date(2026, 7, 20),
    )
    start, end = get_current_cycle_for_meter(meter, date(2026, 6, 1))
    assert (start, end) == (date(2026, 5, 14), date(2026, 7, 19))


def test_last_assessment_date_alone_estimates_end_via_cycle_length():
    # Only the start has been corrected so far (the next visit hasn't
    # happened yet) - the end is a placeholder estimate until it does.
    meter = Meter(
        meter_number="EB-1",
        cycle_length_months=2,
        last_assessment_date=date(2026, 5, 14),
    )
    start, end = get_current_cycle_for_meter(meter, date(2026, 6, 1))
    assert (start, end) == (date(2026, 5, 14), date(2026, 7, 13))
