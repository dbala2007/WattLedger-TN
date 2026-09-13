"""Ensures the household's default tariff plan, meters, and reading history
exist - without anyone having to re-enter them by hand every time the
local dev database is reset (e.g. after a schema change during
development).

IMPORTANT: These are the household's own entered figures, not verified
TNERC/TNPDCL data. PRP.md section 4's tariff-source policy still applies -
check the latest TNERC order and TNPDCL billing guidance, and record the
real order number/date in source_reference, before trusting this for a
real bill.
"""

from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.core.logging import get_logger
from app.models.enums import BillingFrequency, SolarMode
from app.repositories import meter_repository, tariff_repository, user_repository
from app.schemas.tariff import SubsidyRuleCreate, TariffSlabCreate
from app.services import meter_service, reading_service, tariff_service

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
        source_reference=(
            "PLACEHOLDER - source unknown, verify against the real TNERC order/"
            "TNPDCL guidance before trusting for a real bill (PRP.md section 4)."
        ),
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


# This household's own account - meters/readings are per-user data (unlike
# the shared tariff plan above), so re-seeding them for every new signup
# would leak one person's usage history into someone else's fresh account.
# Restricting the seed to this specific email means only this household's
# own account gets its data restored after a dev database reset.
OWNER_EMAIL = "dbala2007@gmail.com"

# (reading_date, eb_units, solar_units) - solar_units is None for the
# non-solar meter. Captured from what was actually entered through the app.
_SOLAR_METER_READINGS = [
    (date(2026, 7, 26), Decimal("1786.4"), Decimal("3629.6")),
    (date(2026, 7, 27), Decimal("1795.1"), Decimal("3638.4")),
    (date(2026, 7, 28), Decimal("1803.2"), Decimal("3646.6")),
    (date(2026, 7, 29), Decimal("1810.6"), Decimal("3656.2")),
    (date(2026, 7, 30), Decimal("1819.6"), Decimal("3666.2")),
    (date(2026, 7, 31), Decimal("1828.8"), Decimal("3674.4")),
    (date(2026, 8, 1), Decimal("1837.5"), Decimal("3684.9")),
    (date(2026, 8, 2), Decimal("1846.7"), Decimal("3693.5")),
    (date(2026, 8, 3), Decimal("1854.8"), Decimal("3701.5")),
    (date(2026, 8, 4), Decimal("1862.4"), Decimal("3712.4")),
    (date(2026, 8, 5), Decimal("1870.1"), Decimal("3723.3")),
    (date(2026, 8, 6), Decimal("1876.9"), Decimal("3728.6")),
    (date(2026, 8, 7), Decimal("1883.7"), Decimal("3734.3")),
    (date(2026, 8, 8), Decimal("1891.1"), Decimal("3742.1")),
    (date(2026, 8, 9), Decimal("1900.0"), Decimal("3753.0")),
    (date(2026, 8, 10), Decimal("1911.3"), Decimal("3762.9")),
    (date(2026, 8, 11), Decimal("1917.7"), Decimal("3774.5")),
    (date(2026, 8, 12), Decimal("1926.3"), Decimal("3785.6")),
    (date(2026, 8, 13), Decimal("1933.3"), Decimal("3792.3")),
    (date(2026, 8, 14), Decimal("1940.1"), Decimal("3804.2")),
    (date(2026, 8, 15), Decimal("1947.9"), Decimal("3814.9")),
    (date(2026, 8, 16), Decimal("1956.1"), Decimal("3828.3")),
    (date(2026, 8, 17), Decimal("1964.5"), Decimal("3838.4")),
    (date(2026, 8, 18), Decimal("1973.3"), Decimal("3849.4")),
    (date(2026, 8, 19), Decimal("1980.3"), Decimal("3856.8")),
    (date(2026, 8, 20), Decimal("1987.4"), Decimal("3867.3")),
    (date(2026, 8, 21), Decimal("1994.7"), Decimal("3877.6")),
    (date(2026, 8, 22), Decimal("2002.7"), Decimal("3890.0")),
    (date(2026, 8, 23), Decimal("2010.3"), Decimal("3900.6")),
]

_NORMAL_METER_READINGS = [
    (date(2026, 7, 26), Decimal("9792.2"), None),
    (date(2026, 7, 27), Decimal("9798.6"), None),
    (date(2026, 7, 28), Decimal("9808.6"), None),
    (date(2026, 7, 29), Decimal("9818.3"), None),
    (date(2026, 7, 30), Decimal("9824.1"), None),
    (date(2026, 7, 31), Decimal("9833.2"), None),
    (date(2026, 8, 1), Decimal("9840.6"), None),
    (date(2026, 8, 2), Decimal("9847.3"), None),
    (date(2026, 8, 3), Decimal("9853.5"), None),
    (date(2026, 8, 4), Decimal("9860.3"), None),
    (date(2026, 8, 5), Decimal("9866.9"), None),
    (date(2026, 8, 6), Decimal("9872.2"), None),
    (date(2026, 8, 7), Decimal("9879.1"), None),
    (date(2026, 8, 8), Decimal("9885.4"), None),
    (date(2026, 8, 9), Decimal("9892.3"), None),
    (date(2026, 8, 10), Decimal("9894.9"), None),
    (date(2026, 8, 11), Decimal("9900.5"), None),
    (date(2026, 8, 12), Decimal("9906.3"), None),
    (date(2026, 8, 13), Decimal("9916.2"), None),
    (date(2026, 8, 14), Decimal("9921.2"), None),
    (date(2026, 8, 15), Decimal("9927.6"), None),
    (date(2026, 8, 16), Decimal("9934.8"), None),
    (date(2026, 8, 17), Decimal("9941.5"), None),
    (date(2026, 8, 18), Decimal("9948.5"), None),
    (date(2026, 8, 19), Decimal("9953.4"), None),
    (date(2026, 8, 20), Decimal("9958.5"), None),
    (date(2026, 8, 21), Decimal("9964.9"), None),
    (date(2026, 8, 22), Decimal("9971.2"), None),
    (date(2026, 8, 23), Decimal("9977.9"), None),
]

_DEFAULT_METERS = [
    {
        "meter_number": "09-434-005-3054",
        "display_name": "Solar EB 3054",
        "solar_mode": SolarMode.ON_GRID,
        "readings": _SOLAR_METER_READINGS,
    },
    {
        "meter_number": "09-434-005-2888",
        "display_name": "Normal EB 2888",
        "solar_mode": SolarMode.NONE,
        "readings": _NORMAL_METER_READINGS,
    },
]

_METER_BILLING_CYCLE_REFERENCE_DATE = date(2026, 7, 26)


def seed_default_meters_if_missing(session: Session) -> None:
    """Recreates OWNER_EMAIL's two meters and their full reading history,
    through the same create_meter/create_reading calls the app itself
    uses (so balances are computed the normal way, not copied verbatim).

    Does nothing if that account doesn't exist yet (nobody to attach
    meters to) or already has meters (never overwrites real data with
    this snapshot).
    """
    user = user_repository.get_by_email(session, OWNER_EMAIL)
    if user is None:
        return
    if meter_repository.list_all(session, user.id):
        return

    for meter_data in _DEFAULT_METERS:
        meter = meter_service.create_meter(
            session,
            user_id=user.id,
            meter_number=meter_data["meter_number"],
            display_name=meter_data["display_name"],
            solar_mode=meter_data["solar_mode"],
            billing_cycle_reference_date=_METER_BILLING_CYCLE_REFERENCE_DATE,
        )
        for reading_date, eb_units, solar_units in meter_data["readings"]:
            reading_service.create_reading(
                session,
                meter_id=meter.id,
                user_id=user.id,
                reading_date=reading_date,
                eb_units=eb_units,
                solar_units=solar_units,
            )

    logger.info("Seeded default meters and reading history for %s.", OWNER_EMAIL)
