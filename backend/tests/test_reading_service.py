"""Service-level tests: these go through the real repository + SQLite
database (an in-memory one, via the `session` fixture), so they verify the
whole create/edit/delete + recalculation flow end to end.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import NotFoundError
from app.domain.readings import ReadingValidationError
from app.models.enums import SolarMode
from app.services import meter_service, reading_service


def _make_meter(session, user_id, solar_mode=SolarMode.NONE, meter_number="EB-001"):
    return meter_service.create_meter(session, user_id=user_id, meter_number=meter_number, solar_mode=solar_mode)


def test_first_reading_for_a_meter_has_no_balance(session, user_id):
    meter = _make_meter(session, user_id)
    reading = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    assert reading.eb_balance is None


def test_normal_next_day_balance(session, user_id):
    meter = _make_meter(session, user_id)
    reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    second = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 2), eb_units=Decimal("1008.5")
    )
    assert second.eb_balance == Decimal("8.5")


def test_decimal_reading_is_stored_precisely(session, user_id):
    meter = _make_meter(session, user_id)
    reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("12500.4")
    )
    second = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 2), eb_units=Decimal("12508.9")
    )
    assert second.eb_balance == Decimal("8.5")


def test_same_date_duplicate_is_rejected(session, user_id):
    meter = _make_meter(session, user_id)
    reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    with pytest.raises(ReadingValidationError):
        reading_service.create_reading(
            session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1005.0")
        )


def test_lower_cumulative_reading_is_rejected(session, user_id):
    meter = _make_meter(session, user_id)
    reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    with pytest.raises(ReadingValidationError):
        reading_service.create_reading(
            session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 2), eb_units=Decimal("990.0")
        )


def test_missing_solar_reading_is_rejected_when_solar_enabled(session, user_id):
    meter = _make_meter(session, user_id, solar_mode=SolarMode.ON_GRID)
    with pytest.raises(ReadingValidationError):
        reading_service.create_reading(
            session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
        )


def test_non_solar_meter_does_not_require_solar_units(session, user_id):
    meter = _make_meter(session, user_id, solar_mode=SolarMode.NONE)
    reading = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    assert reading.solar_units is None
    assert reading.solar_balance is None


def test_on_grid_meter_tracks_solar_balance(session, user_id):
    meter = _make_meter(session, user_id, solar_mode=SolarMode.ON_GRID)
    reading_service.create_reading(
        session,
        meter_id=meter.id,
        user_id=user_id,
        reading_date=date(2026, 5, 1),
        eb_units=Decimal("1000.0"),
        solar_units=Decimal("500.0"),
    )
    second = reading_service.create_reading(
        session,
        meter_id=meter.id,
        user_id=user_id,
        reading_date=date(2026, 5, 2),
        eb_units=Decimal("1008.5"),
        solar_units=Decimal("506.2"),
    )
    assert second.solar_balance == Decimal("6.2")


def test_off_grid_meter_tracks_solar_balance(session, user_id):
    meter = _make_meter(session, user_id, solar_mode=SolarMode.OFF_GRID)
    reading_service.create_reading(
        session,
        meter_id=meter.id,
        user_id=user_id,
        reading_date=date(2026, 5, 1),
        eb_units=Decimal("1000.0"),
        solar_units=Decimal("200.0"),
    )
    second = reading_service.create_reading(
        session,
        meter_id=meter.id,
        user_id=user_id,
        reading_date=date(2026, 5, 2),
        eb_units=Decimal("1006.0"),
        solar_units=Decimal("204.0"),
    )
    assert second.solar_balance == Decimal("4.0")


def test_backdated_reading_recalculates_next_reading(session, user_id):
    meter = _make_meter(session, user_id)
    reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    day3 = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 3), eb_units=Decimal("1015.0")
    )
    assert day3.eb_balance == Decimal("15.0")

    day2 = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 2), eb_units=Decimal("1008.5")
    )
    assert day2.eb_balance == Decimal("8.5")

    all_readings = reading_service.list_readings(session, meter.id, user_id)
    day3_after = next(r for r in all_readings if r.reading_date == date(2026, 5, 3))
    assert day3_after.eb_balance == Decimal("6.5")


def test_historical_edit_recalculates_downstream_balance(session, user_id):
    meter = _make_meter(session, user_id)
    day1 = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    day2 = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 2), eb_units=Decimal("1008.5")
    )
    assert day2.eb_balance == Decimal("8.5")

    reading_service.update_reading(session, day1.id, user_id, eb_units=Decimal("1002.0"))

    refreshed = reading_service.list_readings(session, meter.id, user_id)
    day2_after = next(r for r in refreshed if r.reading_date == date(2026, 5, 2))
    assert day2_after.eb_balance == Decimal("6.5")


def test_historical_delete_recalculates_downstream_balance(session, user_id):
    meter = _make_meter(session, user_id)
    reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    day2 = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 2), eb_units=Decimal("1008.5")
    )
    day3 = reading_service.create_reading(
        session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 3), eb_units=Decimal("1015.0")
    )
    assert day3.eb_balance == Decimal("6.5")

    reading_service.delete_reading(session, day2.id, user_id)

    refreshed = reading_service.list_readings(session, meter.id, user_id)
    assert len(refreshed) == 2
    day3_after = next(r for r in refreshed if r.reading_date == date(2026, 5, 3))
    assert day3_after.eb_balance == Decimal("15.0")


def test_multiple_meters_are_independent(session, user_id):
    meter_a = _make_meter(session, user_id, meter_number="EB-A")
    meter_b = _make_meter(session, user_id, meter_number="EB-B")

    reading_service.create_reading(
        session, meter_id=meter_a.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0")
    )
    a2 = reading_service.create_reading(
        session, meter_id=meter_a.id, user_id=user_id, reading_date=date(2026, 5, 2), eb_units=Decimal("1010.0")
    )

    reading_service.create_reading(
        session, meter_id=meter_b.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("5000.0")
    )
    b2 = reading_service.create_reading(
        session, meter_id=meter_b.id, user_id=user_id, reading_date=date(2026, 5, 2), eb_units=Decimal("5003.0")
    )

    assert a2.eb_balance == Decimal("10.0")
    assert b2.eb_balance == Decimal("3.0")


def test_create_reading_for_unknown_meter_raises_not_found(session, user_id):
    with pytest.raises(NotFoundError):
        reading_service.create_reading(
            session,
            meter_id="does-not-exist",
            user_id=user_id,
            reading_date=date(2026, 5, 1),
            eb_units=Decimal("1000.0"),
        )


def test_reading_for_another_users_meter_raises_not_found(session, user_id):
    from tests.conftest import create_test_user

    other = create_test_user(session, "other2@example.com")

    meter = _make_meter(session, user_id)

    with pytest.raises(NotFoundError):
        reading_service.create_reading(
            session,
            meter_id=meter.id,
            user_id=other.id,
            reading_date=date(2026, 5, 1),
            eb_units=Decimal("1000.0"),
        )
