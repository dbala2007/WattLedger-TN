"""Billing-cycle window calculation.

A meter's billing cycle does not necessarily start on the 1st of an
odd/even month (PRP.md section 6), so this works out cycle windows by
repeatedly stepping a meter-specific anchor date (billing_cycle_reference_date)
forward or backward by the meter's cycle length, rather than assuming
anything about calendar months.
"""

import calendar
from datetime import date, timedelta

from app.models.meter import Meter


def _add_months(d: date, months: int) -> date:
    """Add (or subtract, if negative) whole months to a date, clamping the
    day if the target month is shorter (e.g. 31 Jan + 1 month -> 28/29 Feb).
    """
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def get_cycle_containing(
    reference_date: date,
    cycle_length_months: int,
    target_date: date,
) -> tuple[date, date]:
    """Return (period_start, period_end) of the cycle - anchored at
    reference_date, stepping by cycle_length_months - that contains
    target_date. period_end is the day before the following cycle starts,
    so cycles never overlap and never leave a gap.
    """
    if cycle_length_months <= 0:
        raise ValueError("cycle_length_months must be a positive number of months.")

    start = reference_date

    # Step forward while the next cycle would still end on or before the
    # target date (i.e. target is further ahead than the current cycle).
    while _add_months(start, cycle_length_months) <= target_date:
        start = _add_months(start, cycle_length_months)

    # Step backward while the current cycle starts after the target date
    # (i.e. target is further in the past than the current cycle).
    while start > target_date:
        start = _add_months(start, -cycle_length_months)

    period_end = _add_months(start, cycle_length_months) - timedelta(days=1)
    return start, period_end


def get_current_cycle_for_meter(meter: Meter, as_of_date: date) -> tuple[date, date]:
    """Convenience wrapper: the current cycle window for this meter.

    TN EB billing cycles are not a fixed calendar interval (CLAUDE.md
    section 6) - the real cycle length depends on when the meter reader
    physically visits, which varies each time. So once the user has
    recorded last_assessment_date (the day the meter was actually last
    read), that date - not cycle_length_months arithmetic - becomes the
    authoritative start of the current cycle, overriding the fixed-interval
    calculation below entirely. The end date is next_expected_assessment_date
    if the user has entered their own correction/estimate of the next visit,
    or a cycle_length_months-based placeholder otherwise, used only until
    they correct it once the real date is known.

    Falls back to the fixed-interval calculation (get_cycle_containing) for
    a meter that has never had an assessment date recorded, so existing
    meters behave exactly as before until the user starts correcting dates.
    """
    if meter.last_assessment_date is not None:
        period_start = meter.last_assessment_date
        period_end = (
            meter.next_expected_assessment_date - timedelta(days=1)
            if meter.next_expected_assessment_date is not None
            else _add_months(period_start, meter.cycle_length_months) - timedelta(days=1)
        )
        return period_start, period_end

    if meter.billing_cycle_reference_date is None:
        raise ValueError(
            f"Meter {meter.id} has no billing_cycle_reference_date configured - "
            "set one before computing a billing cycle."
        )
    return get_cycle_containing(meter.billing_cycle_reference_date, meter.cycle_length_months, as_of_date)
