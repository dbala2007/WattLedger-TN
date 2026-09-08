"""Integration tests: tariff plan creation, reading entry, and bill
estimation wired together through the real repositories and an in-memory
SQLite database (the `session` fixture).
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import TariffConfigurationError
from app.models.enums import SolarMode
from app.schemas.tariff import SubsidyRuleCreate, TariffSlabCreate
from app.services import billing_service, meter_service, reading_service, tariff_service

PLAN_DATE = date(2026, 5, 10)


def _seed_example_tariff_plan(session, effective_from=PLAN_DATE, effective_to=None, fixed_charge="50"):
    return tariff_service.create_tariff_plan(
        session,
        name="TN Domestic Example",
        provider="TANGEDCO",
        consumer_category="DOMESTIC",
        effective_from=effective_from,
        effective_to=effective_to,
        billing_frequency="BI_MONTHLY",
        fixed_charge=Decimal(fixed_charge),
        source_reference="EXAMPLE/PLACEHOLDER - not a verified TNERC order",
        active=True,
        subsidy_rules=[
            SubsidyRuleCreate(
                rule_name="cycle_upto_500", consumption_min=Decimal("0"), consumption_max=Decimal("500"),
                free_units=Decimal("200"), effective_from=effective_from, effective_to=effective_to,
            ),
            SubsidyRuleCreate(
                rule_name="cycle_above_500", consumption_min=Decimal("500.0001"), consumption_max=None,
                free_units=Decimal("100"), effective_from=effective_from, effective_to=effective_to,
            ),
        ],
        slabs=[
            TariffSlabCreate(rule_group="cycle_upto_500", from_unit=Decimal("0"), to_unit=Decimal("100"), rate_per_unit=Decimal("3.00"), sort_order=1),
            TariffSlabCreate(rule_group="cycle_upto_500", from_unit=Decimal("100"), to_unit=Decimal("200"), rate_per_unit=Decimal("4.00"), sort_order=2),
            TariffSlabCreate(rule_group="cycle_upto_500", from_unit=Decimal("200"), to_unit=None, rate_per_unit=Decimal("5.00"), sort_order=3),
            TariffSlabCreate(rule_group="cycle_above_500", from_unit=Decimal("0"), to_unit=Decimal("100"), rate_per_unit=Decimal("4.00"), sort_order=1),
            TariffSlabCreate(rule_group="cycle_above_500", from_unit=Decimal("100"), to_unit=Decimal("200"), rate_per_unit=Decimal("5.00"), sort_order=2),
            TariffSlabCreate(rule_group="cycle_above_500", from_unit=Decimal("200"), to_unit=Decimal("500"), rate_per_unit=Decimal("6.50"), sort_order=3),
            TariffSlabCreate(rule_group="cycle_above_500", from_unit=Decimal("500"), to_unit=None, rate_per_unit=Decimal("8.00"), sort_order=4),
        ],
    )


def _meter_with_cycle(session, user_id, reference_date=date(2026, 5, 1), cycle_length_months=2):
    meter = meter_service.create_meter(
        session, user_id=user_id, meter_number="EB-1", solar_mode=SolarMode.NONE,
        billing_cycle_reference_date=reference_date,
    )
    meter.cycle_length_months = cycle_length_months
    session.add(meter)
    session.commit()
    session.refresh(meter)
    return meter


def test_bill_estimate_with_no_readings_has_no_breakdown(session, user_id):
    _seed_example_tariff_plan(session)
    meter = _meter_with_cycle(session, user_id)
    estimate = billing_service.estimate_current_bill(session, meter.id, user_id, as_of_date=date(2026, 5, 15))
    assert estimate.reading_count == 0
    assert estimate.breakdown is None
    assert estimate.note is not None


def test_bill_estimate_sums_readings_within_cycle_and_applies_tariff(session, user_id):
    _seed_example_tariff_plan(session)
    meter = _meter_with_cycle(session, user_id, reference_date=date(2026, 5, 1))

    # Cycle: 2026-05-01 .. 2026-06-30. Opening reading just before the cycle.
    reading_service.create_reading(session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 4, 30), eb_units=Decimal("1000.0"))
    reading_service.create_reading(session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 15), eb_units=Decimal("1150.0"))
    reading_service.create_reading(session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 6, 1), eb_units=Decimal("1300.0"))

    estimate = billing_service.estimate_current_bill(session, meter.id, user_id, as_of_date=date(2026, 6, 15))

    # Cycle consumption = 1300 - 1000 = 300 (the 4/30 reading is outside the
    # cycle and only supplies the opening value).
    assert estimate.total_eb_units == Decimal("300.0")
    assert estimate.breakdown is not None
    assert estimate.breakdown.rule_group == "cycle_upto_500"
    assert estimate.breakdown.chargeable_units == Decimal("100.0")  # 300 - 200 free


def test_bill_estimate_uses_tariff_version_effective_during_billing_period(session, user_id):
    # Old plan covers up to just before the new one starts.
    _seed_example_tariff_plan(session, effective_from=date(2025, 1, 1), effective_to=date(2026, 5, 9), fixed_charge="20")
    _seed_example_tariff_plan(session, effective_from=PLAN_DATE, effective_to=None, fixed_charge="50")

    meter = _meter_with_cycle(session, user_id, reference_date=date(2026, 5, 1))
    reading_service.create_reading(session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 1), eb_units=Decimal("1000.0"))
    reading_service.create_reading(session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 20), eb_units=Decimal("1050.0"))

    estimate = billing_service.estimate_current_bill(session, meter.id, user_id, as_of_date=date(2026, 5, 20))
    assert estimate.breakdown.fixed_charge == Decimal("50")  # the new plan, not the 20-fixed old one


def test_bill_estimate_raises_when_no_tariff_plan_configured(session, user_id):
    meter = _meter_with_cycle(session, user_id)
    reading_service.create_reading(session, meter_id=meter.id, user_id=user_id, reading_date=date(2026, 5, 5), eb_units=Decimal("1000.0"))
    with pytest.raises(TariffConfigurationError):
        billing_service.estimate_current_bill(session, meter.id, user_id, as_of_date=date(2026, 5, 5))


def test_current_billing_cycle_endpoint_matches_meter_settings(session, user_id):
    meter = _meter_with_cycle(session, user_id, reference_date=date(2026, 5, 10), cycle_length_months=2)
    window = billing_service.get_current_billing_cycle(session, meter.id, user_id, as_of_date=date(2026, 6, 1))
    assert window.period_start == date(2026, 5, 10)
    assert window.period_end == date(2026, 7, 9)
