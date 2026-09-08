"""Tests for the pure domain logic in app.domain.readings - no database
involved, so these run fast and pin down the calculation/validation rules
directly.
"""

from datetime import date
from decimal import Decimal

from app.domain.readings import calculate_balance, recalculate_chain, validate_reading
from app.models.enums import SolarMode
from app.models.reading import MeterReading


def test_first_reading_has_no_balance():
    assert calculate_balance(Decimal("100.0"), None) is None


def test_normal_next_day_balance():
    assert calculate_balance(Decimal("108.5"), Decimal("100.0")) == Decimal("8.5")


def test_decimal_reading_balance_is_exact():
    # This is exactly the example from PRP.md section 2.
    assert calculate_balance(Decimal("12508.9"), Decimal("12500.4")) == Decimal("8.5")


def test_validate_reading_lower_eb_units_is_rejected():
    errors = validate_reading(
        solar_mode=SolarMode.NONE,
        eb_units=Decimal("95.0"),
        solar_units=None,
        previous_eb_units=Decimal("100.0"),
        previous_solar_units=None,
        date_already_has_reading=False,
    )
    assert any("EB Units" in e for e in errors)


def test_validate_reading_lower_solar_units_is_rejected():
    errors = validate_reading(
        solar_mode=SolarMode.ON_GRID,
        eb_units=Decimal("110.0"),
        solar_units=Decimal("45.0"),
        previous_eb_units=Decimal("100.0"),
        previous_solar_units=Decimal("50.0"),
        date_already_has_reading=False,
    )
    assert any("Solar Unit" in e for e in errors)


def test_validate_reading_duplicate_date_is_rejected():
    errors = validate_reading(
        solar_mode=SolarMode.NONE,
        eb_units=Decimal("110.0"),
        solar_units=None,
        previous_eb_units=Decimal("100.0"),
        previous_solar_units=None,
        date_already_has_reading=True,
    )
    assert any("already exists" in e for e in errors)


def test_validate_reading_missing_solar_when_required_is_rejected():
    errors = validate_reading(
        solar_mode=SolarMode.OFF_GRID,
        eb_units=Decimal("110.0"),
        solar_units=None,
        previous_eb_units=Decimal("100.0"),
        previous_solar_units=Decimal("50.0"),
        date_already_has_reading=False,
    )
    assert any("Solar Unit is required" in e for e in errors)


def test_validate_reading_non_solar_meter_does_not_require_solar():
    errors = validate_reading(
        solar_mode=SolarMode.NONE,
        eb_units=Decimal("110.0"),
        solar_units=None,
        previous_eb_units=Decimal("100.0"),
        previous_solar_units=None,
        date_already_has_reading=False,
    )
    assert errors == []


def test_validate_reading_valid_reading_has_no_errors():
    errors = validate_reading(
        solar_mode=SolarMode.ON_GRID,
        eb_units=Decimal("110.0"),
        solar_units=Decimal("55.0"),
        previous_eb_units=Decimal("100.0"),
        previous_solar_units=Decimal("50.0"),
        date_already_has_reading=False,
    )
    assert errors == []


def _reading(day: int, eb_units: str, solar_units: str | None = None) -> MeterReading:
    return MeterReading(
        meter_id="m1",
        reading_date=date(2026, 5, day),
        eb_units=Decimal(eb_units),
        solar_units=Decimal(solar_units) if solar_units is not None else None,
    )


def test_recalculate_chain_computes_balances_in_date_order():
    readings = [_reading(1, "1000.0"), _reading(2, "1008.5"), _reading(3, "1015.0")]
    recalculate_chain(readings)

    assert readings[0].eb_balance is None
    assert readings[1].eb_balance == Decimal("8.5")
    assert readings[2].eb_balance == Decimal("6.5")


def test_recalculate_chain_after_backdated_insert():
    # Original chain: day 1 -> day 3. A day-2 reading is inserted afterwards,
    # which should change day 3's balance to be relative to day 2, not day 1.
    day1 = _reading(1, "1000.0")
    day3 = _reading(3, "1015.0")
    recalculate_chain([day1, day3])
    assert day3.eb_balance == Decimal("15.0")

    day2 = _reading(2, "1008.5")
    readings = sorted([day1, day2, day3], key=lambda r: r.reading_date)
    recalculate_chain(readings)

    assert day2.eb_balance == Decimal("8.5")
    assert day3.eb_balance == Decimal("6.5")
