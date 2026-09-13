from datetime import date
from decimal import Decimal

from app.db.seed_data import OWNER_EMAIL, seed_default_meters_if_missing, seed_default_tariff_plan_if_missing
from app.domain.tariffs import calculate_bill
from app.models.enums import SolarMode
from app.repositories import meter_repository, reading_repository, tariff_repository, user_repository
from app.services import tariff_service


def test_seed_creates_exactly_one_plan_with_non_overlapping_rules(session):
    seed_default_tariff_plan_if_missing(session)

    plans = tariff_repository.list_plans(session)
    assert len(plans) == 1

    _plan, rules, _slabs = tariff_service.get_tariff_plan_bundle(session, plans[0].id)
    # 500 and 500.0001 must not both be claimed by the same-or-overlapping
    # rules - this is exactly the bug this seed exists to avoid reintroducing.
    below = next(r for r in rules if r.rule_name == "Below_500")
    above = next(r for r in rules if r.rule_name == "Above_500")
    assert below.consumption_max == Decimal("500")
    assert above.consumption_min > below.consumption_max


def test_seed_is_a_no_op_when_a_plan_already_exists(session):
    seed_default_tariff_plan_if_missing(session)
    seed_default_tariff_plan_if_missing(session)  # must not create a second plan

    assert len(tariff_repository.list_plans(session)) == 1


def test_seeded_plan_produces_a_bill_without_a_configuration_error(session):
    """The overlap bug this seed exists to avoid would surface as a
    TariffConfigurationError right at the 500-unit boundary - so calculate a
    bill exactly there as a regression guard.
    """
    seed_default_tariff_plan_if_missing(session)
    plans = tariff_repository.list_plans(session)
    plan, rules, slabs = tariff_service.get_tariff_plan_bundle(session, plans[0].id)

    breakdown = calculate_bill(
        total_units=Decimal("500"),
        tariff_plan=plan,
        subsidy_rules=rules,
        slabs=slabs,
        as_of_date=date(2026, 8, 1),
    )
    assert breakdown.rule_group == "Below_500"


def test_seed_meters_does_nothing_when_owner_account_does_not_exist(session):
    seed_default_meters_if_missing(session)
    assert user_repository.get_by_email(session, OWNER_EMAIL) is None


def test_seed_meters_creates_both_meters_with_correct_balances(session):
    from tests.conftest import create_test_user

    owner = create_test_user(session, OWNER_EMAIL)

    seed_default_meters_if_missing(session)

    meters = meter_repository.list_all(session, owner.id)
    assert len(meters) == 2

    solar_meter = next(m for m in meters if m.solar_mode == SolarMode.ON_GRID)
    readings = reading_repository.list_for_meter(session, solar_meter.id)
    assert len(readings) == 29
    # First reading has no prior reading to diff against.
    first = min(readings, key=lambda r: r.reading_date)
    assert first.eb_balance is None
    # A day with a known, hand-checked balance.
    day2 = next(r for r in readings if r.reading_date == date(2026, 7, 27))
    assert day2.eb_balance == Decimal("8.7")
    assert day2.solar_balance == Decimal("8.8")


def test_seed_meters_is_a_no_op_when_owner_already_has_meters(session):
    from tests.conftest import create_test_user

    owner = create_test_user(session, OWNER_EMAIL)
    seed_default_meters_if_missing(session)
    seed_default_meters_if_missing(session)  # must not duplicate

    assert len(meter_repository.list_all(session, owner.id)) == 2


def test_seed_meters_never_seeds_for_a_different_account(session):
    from tests.conftest import create_test_user

    other = create_test_user(session, "someone-else@example.com")
    seed_default_meters_if_missing(session)

    assert meter_repository.list_all(session, other.id) == []
