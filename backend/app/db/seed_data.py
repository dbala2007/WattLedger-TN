"""Ensures a default tariff plan exists so the billing engine always has
something to calculate against - without anyone having to re-enter it by
hand every time the local dev database is reset (e.g. after a schema
change during development).

IMPORTANT: These are the household's own entered figures, not a verified
TNERC/TNPDCL order. PRP.md section 4's tariff-source policy still applies -
check the latest TNERC order and TNPDCL billing guidance, and record the
real order number/date in source_reference, before trusting this for a
real bill.
"""

from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.core.logging import get_logger
from app.models.enums import BillingFrequency
from app.repositories import tariff_repository
from app.schemas.tariff import SubsidyRuleCreate, TariffSlabCreate
from app.services import tariff_service

logger = get_logger(__name__)

EFFECTIVE_FROM = date(2026, 7, 26)


def seed_default_tariff_plan_if_missing(session: Session) -> None:
    """Does nothing if any tariff plan already exists - this only fills in
    a fresh/empty database, it never overwrites a plan someone has since
    edited through the app.
    """
    if tariff_repository.list_plans(session):
        return

    plan, rules, slabs = tariff_service.create_tariff_plan(
        session,
        name="TN Domestic",
        provider="TANGEDCO",
        consumer_category="DOMESTIC",
        effective_from=EFFECTIVE_FROM,
        effective_to=None,
        billing_frequency=BillingFrequency.BI_MONTHLY,
        fixed_charge=Decimal("0"),
        source_reference="Vijay",
        active=True,
        subsidy_rules=[
            SubsidyRuleCreate(
                rule_name="Below_500",
                consumption_min=Decimal("0"),
                consumption_max=Decimal("500"),
                free_units=Decimal("200"),
                effective_from=EFFECTIVE_FROM,
            ),
            SubsidyRuleCreate(
                # Starts just above 500, not at 0, so this rule and
                # Below_500 never both match the same consumption value -
                # see docs/decisions/0003-irregular-billing-cycles.md's
                # sibling note in CLAUDE.md section 5 on non-overlapping bands.
                rule_name="Above_500",
                consumption_min=Decimal("500.0001"),
                consumption_max=None,
                free_units=Decimal("100"),
                effective_from=EFFECTIVE_FROM,
            ),
        ],
        slabs=[
            TariffSlabCreate(rule_group="Below_500", from_unit=Decimal("0"), to_unit=Decimal("200"), rate_per_unit=Decimal("0"), sort_order=1),
            TariffSlabCreate(rule_group="Below_500", from_unit=Decimal("201"), to_unit=Decimal("400"), rate_per_unit=Decimal("4.7"), sort_order=2),
            TariffSlabCreate(rule_group="Below_500", from_unit=Decimal("401"), to_unit=Decimal("500"), rate_per_unit=Decimal("6.3"), sort_order=3),
            TariffSlabCreate(rule_group="Above_500", from_unit=Decimal("0"), to_unit=Decimal("100"), rate_per_unit=Decimal("0"), sort_order=1),
            TariffSlabCreate(rule_group="Above_500", from_unit=Decimal("101"), to_unit=Decimal("400"), rate_per_unit=Decimal("4.4"), sort_order=2),
            TariffSlabCreate(rule_group="Above_500", from_unit=Decimal("401"), to_unit=Decimal("500"), rate_per_unit=Decimal("6.3"), sort_order=3),
            TariffSlabCreate(rule_group="Above_500", from_unit=Decimal("501"), to_unit=Decimal("600"), rate_per_unit=Decimal("8.4"), sort_order=4),
            TariffSlabCreate(rule_group="Above_500", from_unit=Decimal("601"), to_unit=Decimal("800"), rate_per_unit=Decimal("9.45"), sort_order=5),
            TariffSlabCreate(rule_group="Above_500", from_unit=Decimal("801"), to_unit=Decimal("1000"), rate_per_unit=Decimal("10.5"), sort_order=6),
            TariffSlabCreate(rule_group="Above_500", from_unit=Decimal("1001"), to_unit=None, rate_per_unit=Decimal("11.55"), sort_order=7),
        ],
    )
    logger.info("Seeded default tariff plan %s (%s slabs, %s subsidy rules).", plan.id, len(slabs), len(rules))
