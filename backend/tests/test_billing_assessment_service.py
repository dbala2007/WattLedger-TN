"""Tests for the official assessment (meter reader visit) history and the
past-cycle billing history built from it.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlmodel import select

from app.core.timezone import today_local
from app.db.seed_data import backfill_billing_assessments_from_meters
from app.domain.errors import NotFoundError
from app.models.billing_assessment import BillingAssessment
from app.services import billing_assessment_service, billing_service, meter_service, reading_service
from tests.conftest import create_test_user
from tests.test_billing_service import _meter_with_cycle, _seed_example_tariff_plan


def _read(session, meter_id, user_id, reading_date, eb_units):
    reading_service.create_reading(
        session, meter_id=meter_id, user_id=user_id, reading_date=reading_date, eb_units=Decimal(eb_units)
    )


def _visit(session, meter_id, user_id, assessed_on, official_bill_amount=None):
    return billing_assessment_service.create_assessment(
        session, meter_id=meter_id, user_id=user_id, assessed_on=assessed_on,
        official_bill_amount=None if official_bill_amount is None else Decimal(official_bill_amount),
    )


# --- Recording / editing / deleting visits ---


def test_recording_a_visit_moves_the_meters_current_cycle_start(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    _visit(session, meter.id, user_id, date(2026, 5, 29))
    _visit(session, meter.id, user_id, date(2026, 7, 26))

    session.refresh(meter)
    assert meter.last_assessment_date == date(2026, 7, 26)


def test_recording_an_older_visit_does_not_move_current_cycle_back(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    _visit(session, meter.id, user_id, date(2026, 7, 26))
    _visit(session, meter.id, user_id, date(2026, 5, 29))  # filling in history afterwards

    session.refresh(meter)
    assert meter.last_assessment_date == date(2026, 7, 26)


def test_future_visit_is_rejected(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    with pytest.raises(ValueError, match="future"):
        _visit(session, meter.id, user_id, today_local() + timedelta(days=1))


def test_same_date_twice_is_rejected(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    _visit(session, meter.id, user_id, date(2026, 7, 26))
    with pytest.raises(ValueError, match="already recorded"):
        _visit(session, meter.id, user_id, date(2026, 7, 26))


def test_negative_official_amount_is_rejected(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    with pytest.raises(ValueError, match="negative"):
        _visit(session, meter.id, user_id, date(2026, 7, 26), official_bill_amount="-1")


def test_recording_a_visit_clears_a_next_expected_date_it_has_passed(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    meter_service.update_meter(
        session, meter.id, user_id,
        last_assessment_date=date(2026, 5, 29), next_expected_assessment_date=date(2026, 7, 28),
    )
    # A visit before the expected date leaves the expectation in place...
    _visit(session, meter.id, user_id, date(2026, 7, 26))
    session.refresh(meter)
    assert meter.next_expected_assessment_date == date(2026, 7, 28)

    # ...but a visit on/after it means it described a cycle that is now closed.
    _visit(session, meter.id, user_id, date(2026, 7, 30))
    session.refresh(meter)
    assert meter.next_expected_assessment_date is None


def test_editing_the_latest_visit_date_updates_the_meter(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    visit = _visit(session, meter.id, user_id, date(2026, 7, 26))

    billing_assessment_service.update_assessment(
        session, meter_id=meter.id, assessment_id=visit.id, user_id=user_id,
        assessed_on=date(2026, 7, 27), official_bill_amount=Decimal("512.00"), notes="corrected",
    )
    session.refresh(meter)
    assert meter.last_assessment_date == date(2026, 7, 27)


def test_editing_a_visit_onto_another_visits_date_is_rejected(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    _visit(session, meter.id, user_id, date(2026, 5, 29))
    later = _visit(session, meter.id, user_id, date(2026, 7, 26))
    with pytest.raises(ValueError, match="already recorded"):
        billing_assessment_service.update_assessment(
            session, meter_id=meter.id, assessment_id=later.id, user_id=user_id,
            assessed_on=date(2026, 5, 29), official_bill_amount=None, notes=None,
        )


def test_deleting_the_latest_visit_falls_back_to_the_previous_one(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    _visit(session, meter.id, user_id, date(2026, 5, 29))
    latest = _visit(session, meter.id, user_id, date(2026, 7, 26))

    billing_assessment_service.delete_assessment(session, meter_id=meter.id, assessment_id=latest.id, user_id=user_id)
    session.refresh(meter)
    assert meter.last_assessment_date == date(2026, 5, 29)


def test_deleting_the_only_visit_clears_the_meters_assessment_date(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    only = _visit(session, meter.id, user_id, date(2026, 7, 26))

    billing_assessment_service.delete_assessment(session, meter_id=meter.id, assessment_id=only.id, user_id=user_id)
    session.refresh(meter)
    assert meter.last_assessment_date is None


def test_another_users_visits_are_not_visible_or_editable(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    visit = _visit(session, meter.id, user_id, date(2026, 7, 26))
    stranger_id = create_test_user(session, "stranger@example.com").id

    with pytest.raises(NotFoundError):
        billing_assessment_service.list_assessments(session, meter.id, stranger_id)
    with pytest.raises(NotFoundError):
        billing_assessment_service.delete_assessment(
            session, meter_id=meter.id, assessment_id=visit.id, user_id=stranger_id
        )


def test_visit_id_from_a_different_meter_is_not_found(session, user_id):
    meter_a = _meter_with_cycle(session, user_id)
    meter_b = meter_service.create_meter(
        session, user_id=user_id, meter_number="EB-2", billing_cycle_reference_date=date(2026, 5, 1)
    )
    visit_on_b = _visit(session, meter_b.id, user_id, date(2026, 7, 26))
    with pytest.raises(NotFoundError):
        billing_assessment_service.delete_assessment(
            session, meter_id=meter_a.id, assessment_id=visit_on_b.id, user_id=user_id
        )


# --- Older path: setting last_assessment_date directly on the meter ---


def test_setting_meter_last_assessment_date_records_a_visit_once(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    meter_service.update_meter(session, meter.id, user_id, last_assessment_date=date(2026, 7, 26))
    # Older app versions re-send the same date on every meter save - that
    # must not create a duplicate.
    meter_service.update_meter(session, meter.id, user_id, last_assessment_date=date(2026, 7, 26))

    visits = billing_assessment_service.list_assessments(session, meter.id, user_id)
    assert [v.assessed_on for v in visits] == [date(2026, 7, 26)]


def test_failed_meter_update_does_not_leave_a_visit_behind(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    with pytest.raises(ValueError):
        meter_service.update_meter(
            session, meter.id, user_id,
            last_assessment_date=date(2026, 7, 26), next_expected_assessment_date=date(2026, 7, 1),
        )
    assert billing_assessment_service.list_assessments(session, meter.id, user_id) == []


def test_backfill_copies_existing_meter_dates_once(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    # Simulate a meter saved before the history table existed.
    meter.last_assessment_date = date(2026, 7, 26)
    session.add(meter)
    session.commit()

    backfill_billing_assessments_from_meters(session)
    backfill_billing_assessments_from_meters(session)  # it runs on every startup

    rows = session.exec(select(BillingAssessment).where(BillingAssessment.meter_id == meter.id)).all()
    assert [r.assessed_on for r in rows] == [date(2026, 7, 26)]


# --- Billing history (past cycles) ---


def test_history_is_empty_until_two_visits_are_recorded(session, user_id):
    _seed_example_tariff_plan(session)
    meter = _meter_with_cycle(session, user_id)
    _visit(session, meter.id, user_id, date(2026, 5, 29))
    assert billing_service.get_billing_history(session, meter.id, user_id) == []


def test_previous_cycle_bill_sums_only_that_cycles_readings(session, user_id):
    _seed_example_tariff_plan(session)
    meter = _meter_with_cycle(session, user_id)
    _read(session, meter.id, user_id, date(2026, 5, 28), "1000")  # before the cycle - opening value only
    _read(session, meter.id, user_id, date(2026, 6, 15), "1150")
    _read(session, meter.id, user_id, date(2026, 7, 25), "1300")  # last day of the cycle
    _read(session, meter.id, user_id, date(2026, 7, 26), "1310")  # first day of the next cycle
    _visit(session, meter.id, user_id, date(2026, 5, 29))
    _visit(session, meter.id, user_id, date(2026, 7, 26), official_bill_amount="400.00")

    [cycle] = billing_service.get_billing_history(session, meter.id, user_id)

    assert (cycle.estimate.period_start, cycle.estimate.period_end) == (date(2026, 5, 29), date(2026, 7, 25))
    assert cycle.estimate.total_eb_units == Decimal("300")  # 1300 - 1000; the 26 Jul reading is excluded
    assert cycle.estimate.breakdown.rule_group == "cycle_upto_500"
    assert cycle.estimate.breakdown.chargeable_units == Decimal("100")  # 300 - 200 free
    assert cycle.official_bill_amount == Decimal("400.00")
    assert cycle.difference == Decimal("400.00") - cycle.estimate.breakdown.total_estimated_amount


def test_history_is_newest_first_and_meets_the_current_cycle(session, user_id):
    _seed_example_tariff_plan(session)
    meter = _meter_with_cycle(session, user_id)
    _read(session, meter.id, user_id, date(2026, 5, 29), "1000")
    _read(session, meter.id, user_id, date(2026, 7, 26), "1200")
    _read(session, meter.id, user_id, date(2026, 9, 20), "1500")
    for visit_date in (date(2026, 5, 29), date(2026, 7, 26), date(2026, 9, 24)):
        _visit(session, meter.id, user_id, visit_date)

    history = billing_service.get_billing_history(session, meter.id, user_id)
    assert [c.estimate.period_start for c in history] == [date(2026, 7, 26), date(2026, 5, 29)]

    # No gap and no overlap: the newest completed cycle ends the day before
    # the current cycle starts.
    current = billing_service.get_current_billing_cycle(session, meter.id, user_id)
    assert history[0].estimate.period_end + timedelta(days=1) == current.period_start


def test_past_cycle_uses_tariff_effective_then_not_today(session, user_id):
    # Old plan up to 9 May (fixed charge 20), new plan from 10 May (fixed 50).
    _seed_example_tariff_plan(session, effective_from=date(2025, 1, 1), effective_to=date(2026, 5, 9), fixed_charge="20")
    _seed_example_tariff_plan(session, effective_from=date(2026, 5, 10), effective_to=None, fixed_charge="50")
    meter = _meter_with_cycle(session, user_id)
    _read(session, meter.id, user_id, date(2026, 3, 1), "1000")
    _read(session, meter.id, user_id, date(2026, 4, 30), "1100")
    _visit(session, meter.id, user_id, date(2026, 3, 1))
    _visit(session, meter.id, user_id, date(2026, 5, 1))  # cycle 1 Mar .. 30 Apr

    [cycle] = billing_service.get_billing_history(session, meter.id, user_id)
    assert cycle.estimate.breakdown.fixed_charge == Decimal("20")


def test_cycle_without_a_tariff_is_still_listed_with_a_note(session, user_id):
    # The only tariff starts 10 May 2026; the cycle below ends in April.
    _seed_example_tariff_plan(session)
    meter = _meter_with_cycle(session, user_id)
    _read(session, meter.id, user_id, date(2026, 3, 1), "1000")
    _read(session, meter.id, user_id, date(2026, 4, 30), "1100")
    _visit(session, meter.id, user_id, date(2026, 3, 1))
    _visit(session, meter.id, user_id, date(2026, 5, 1))

    [cycle] = billing_service.get_billing_history(session, meter.id, user_id)
    assert cycle.estimate.breakdown is None
    assert cycle.estimate.total_eb_units == Decimal("100")
    assert "Cannot estimate" in cycle.estimate.note
    assert cycle.difference is None


def test_editing_a_historical_reading_updates_the_past_cycle(session, user_id):
    _seed_example_tariff_plan(session)
    meter = _meter_with_cycle(session, user_id)
    _read(session, meter.id, user_id, date(2026, 5, 29), "1000")
    _read(session, meter.id, user_id, date(2026, 7, 25), "1300")
    _visit(session, meter.id, user_id, date(2026, 5, 29))
    _visit(session, meter.id, user_id, date(2026, 7, 26))

    readings = reading_service.list_readings(session, meter.id, user_id)
    last = next(r for r in readings if r.reading_date == date(2026, 7, 25))
    reading_service.update_reading(session, last.id, user_id, eb_units=Decimal("1250"))

    [cycle] = billing_service.get_billing_history(session, meter.id, user_id)
    assert cycle.estimate.total_eb_units == Decimal("250")
