"""Seed the local dev database with an EXAMPLE Tamil Nadu domestic tariff
plan, so the billing engine has something to calculate against.

IMPORTANT: The slab rates below are made-up round numbers for development
and testing only. They are NOT verified TNERC/TNPDCL figures. PRP.md section
4's tariff-source policy requires checking the latest TNERC tariff order and
TNPDCL billing guidance, and recording the real order/source name before
this is ever used for a real bill. Do not treat these numbers as accurate.

Run with (from the backend/ folder):
    uv run python scripts/seed_dev_tariff.py
"""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Running this file directly (not as a -m module) only puts scripts/ itself
# on sys.path, not backend/ - so "import app...." would fail without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.core.logging import get_logger
from app.db.session import create_db_and_tables, engine
from app.models.enums import BillingFrequency
from app.schemas.tariff import SubsidyRuleCreate, TariffSlabCreate
from app.services import tariff_service

logger = get_logger(__name__)

EFFECTIVE_FROM = date(2026, 5, 10)


def seed(session: Session) -> None:
    plan, rules, slabs = tariff_service.create_tariff_plan(
        session,
        name="TN Domestic - EXAMPLE (unverified)",
        provider="TANGEDCO",
        consumer_category="DOMESTIC",
        effective_from=EFFECTIVE_FROM,
        effective_to=None,
        billing_frequency=BillingFrequency.BI_MONTHLY,
        fixed_charge=Decimal("50.00"),
        source_reference=(
            "PLACEHOLDER - replace with the real TNERC order number/date "
            "before using this for a real bill (PRP.md section 4)."
        ),
        active=True,
        subsidy_rules=[
            SubsidyRuleCreate(
                rule_name="cycle_upto_500",
                consumption_min=Decimal("0"),
                consumption_max=Decimal("500"),
                free_units=Decimal("200"),
                effective_from=EFFECTIVE_FROM,
            ),
            SubsidyRuleCreate(
                rule_name="cycle_above_500",
                consumption_min=Decimal("500.0001"),
                consumption_max=None,
                free_units=Decimal("100"),
                effective_from=EFFECTIVE_FROM,
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
    logger.info("Seeded example tariff plan %s (%s slabs, %s subsidy rules).", plan.id, len(slabs), len(rules))


if __name__ == "__main__":
    create_db_and_tables()
    with Session(engine) as session:
        seed(session)
    print("Done. This used PLACEHOLDER tariff rates - see the warning at the top of this file.")
