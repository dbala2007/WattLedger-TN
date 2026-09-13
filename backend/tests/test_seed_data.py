from datetime import date
from decimal import Decimal

from app.db.seed_data import seed_default_tariff_plan_if_missing
from app.domain.tariffs import calculate_bill
from app.repositories import tariff_repository
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
