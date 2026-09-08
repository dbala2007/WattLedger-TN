"""Tests for the tariff plan update path (app.services.tariff_service).

update_tariff_plan edits an existing plan in place, unlike create_tariff_plan
which always inserts a new version - see the docstring on update_tariff_plan
for why that's safe today (no BillingAssessment history references tariff
plans yet).
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import NotFoundError
from app.models.enums import BillingFrequency
from app.schemas.tariff import SubsidyRuleCreate, TariffSlabCreate
from app.services import tariff_service

PLAN_DATE = date(2026, 5, 10)


def _create_example_plan(session):
    plan, rules, slabs = tariff_service.create_tariff_plan(
        session,
        name="TN Domestic Example",
        provider="TANGEDCO",
        consumer_category="DOMESTIC",
        effective_from=PLAN_DATE,
        effective_to=None,
        billing_frequency=BillingFrequency.BI_MONTHLY,
        fixed_charge=Decimal("50"),
        source_reference="EXAMPLE/PLACEHOLDER",
        active=True,
        subsidy_rules=[
            SubsidyRuleCreate(
                rule_name="cycle_upto_500",
                consumption_min=Decimal("0"),
                consumption_max=Decimal("500"),
                free_units=Decimal("200"),
                effective_from=PLAN_DATE,
            ),
        ],
        slabs=[
            TariffSlabCreate(rule_group="cycle_upto_500", from_unit=Decimal("0"), to_unit=None, rate_per_unit=Decimal("2")),
        ],
    )
    return plan


def test_update_tariff_plan_changes_fields(session):
    plan = _create_example_plan(session)

    updated, rules, slabs = tariff_service.update_tariff_plan(
        session,
        plan.id,
        name="TN Domestic Corrected",
        provider="TANGEDCO",
        consumer_category="DOMESTIC",
        effective_from=PLAN_DATE,
        effective_to=None,
        billing_frequency=BillingFrequency.BI_MONTHLY,
        fixed_charge=Decimal("75"),
        source_reference="TNERC Order 1/2026",
        active=True,
        subsidy_rules=[
            SubsidyRuleCreate(
                rule_name="cycle_upto_500",
                consumption_min=Decimal("0"),
                consumption_max=Decimal("500"),
                free_units=Decimal("200"),
                effective_from=PLAN_DATE,
            ),
        ],
        slabs=[
            TariffSlabCreate(rule_group="cycle_upto_500", from_unit=Decimal("0"), to_unit=None, rate_per_unit=Decimal("3")),
        ],
    )

    assert updated.name == "TN Domestic Corrected"
    assert updated.fixed_charge == Decimal("75")
    assert updated.source_reference == "TNERC Order 1/2026"
    assert len(rules) == 1
    assert len(slabs) == 1
    assert slabs[0].rate_per_unit == Decimal("3")


def test_update_tariff_plan_replaces_rules_and_slabs_rather_than_appending(session):
    plan = _create_example_plan(session)

    _, rules, slabs = tariff_service.update_tariff_plan(
        session,
        plan.id,
        name=plan.name,
        provider=plan.provider,
        consumer_category=plan.consumer_category,
        effective_from=plan.effective_from,
        effective_to=plan.effective_to,
        billing_frequency=plan.billing_frequency,
        fixed_charge=plan.fixed_charge,
        source_reference=plan.source_reference,
        active=plan.active,
        subsidy_rules=[
            SubsidyRuleCreate(
                rule_name="cycle_upto_500",
                consumption_min=Decimal("0"),
                consumption_max=Decimal("500"),
                free_units=Decimal("250"),
                effective_from=PLAN_DATE,
            ),
        ],
        slabs=[
            TariffSlabCreate(rule_group="cycle_upto_500", from_unit=Decimal("0"), to_unit=Decimal("100"), rate_per_unit=Decimal("1")),
            TariffSlabCreate(rule_group="cycle_upto_500", from_unit=Decimal("100"), to_unit=None, rate_per_unit=Decimal("2")),
        ],
    )

    # Confirms the old rule/slabs were deleted, not left behind alongside the new ones.
    assert len(rules) == 1
    assert rules[0].free_units == Decimal("250")
    assert len(slabs) == 2


def test_update_unknown_tariff_plan_raises_not_found(session):
    with pytest.raises(NotFoundError):
        tariff_service.update_tariff_plan(
            session,
            "does-not-exist",
            name="x",
            provider="x",
            consumer_category="DOMESTIC",
            effective_from=PLAN_DATE,
            effective_to=None,
            billing_frequency=BillingFrequency.BI_MONTHLY,
            fixed_charge=Decimal("0"),
            source_reference="x",
            active=True,
            subsidy_rules=[],
            slabs=[],
        )
