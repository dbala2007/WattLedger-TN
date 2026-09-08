"""Tariff configuration tables: TariffPlan, TariffSlab, SubsidyRule.

These hold TNERC/TNPDCL regulatory data as editable, effective-dated rows -
never as constants in code (CLAUDE.md section 5). A TariffPlan groups
together the slabs and subsidy rules that were in force for some date range,
so historical bills always keep using the version that was active at the
time, even after a newer TariffPlan is added.

How a TariffSlab connects to a SubsidyRule: both carry a `rule_group`/
`rule_name` string (e.g. "cycle_upto_500") scoped to one tariff_plan_id.
A SubsidyRule's consumption_min/consumption_max says which total-cycle-usage
band selects that rule_name; the TariffSlab rows sharing that same
rule_group are the per-unit slabs charged within that band, once the
SubsidyRule's free_units have been subtracted. This mirrors the rule_groups
example in PRP.md section 4.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel

from app.models.enums import BillingFrequency


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Numeric(14, 4): matches PRP.md's own example threshold of "500.0001",
# i.e. 4 decimal places, with room for large cumulative unit counts.
def _rate_column() -> Column:
    return Column(Numeric(14, 4), nullable=False)


def _nullable_rate_column() -> Column:
    return Column(Numeric(14, 4), nullable=True)


class TariffPlan(SQLModel, table=True):
    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    name: str
    provider: str = Field(default="TANGEDCO")
    consumer_category: str = Field(default="DOMESTIC", index=True)

    effective_from: date = Field(index=True)
    effective_to: date | None = Field(default=None, index=True)

    billing_frequency: BillingFrequency = Field(default=BillingFrequency.BI_MONTHLY)

    # Fixed/service charge applied once per bill, on top of slab charges.
    # Defaults to 0 since not every plan configuration needs one.
    fixed_charge: Decimal = Field(default=Decimal("0"), sa_column=_rate_column())

    # Free text recording the regulatory source, e.g. "TNERC Order No. 5 of
    # 2026, effective 10-May-2026". Required so every estimate can show
    # which order it is based on (CLAUDE.md section 5, NFR-006).
    source_reference: str

    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)


class SubsidyRule(SQLModel, table=True):
    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tariff_plan_id: str = Field(foreign_key="tariffplan.id", index=True)

    # Identifies the consumption band/rule group this subsidy belongs to,
    # e.g. "cycle_upto_500". TariffSlab rows with a matching rule_group,
    # under the same tariff_plan_id, are the slabs used within this band.
    rule_name: str = Field(index=True)

    consumption_min: Decimal = Field(sa_column=_rate_column())
    consumption_max: Decimal | None = Field(default=None, sa_column=_nullable_rate_column())
    free_units: Decimal = Field(sa_column=_rate_column())

    effective_from: date
    effective_to: date | None = None


class TariffSlab(SQLModel, table=True):
    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tariff_plan_id: str = Field(foreign_key="tariffplan.id", index=True)

    rule_group: str = Field(index=True)

    from_unit: Decimal = Field(sa_column=_rate_column())
    # None means "unlimited" - the last slab in a rule_group must leave this
    # as None so every possible chargeable-unit value is covered.
    to_unit: Decimal | None = Field(default=None, sa_column=_nullable_rate_column())
    rate_per_unit: Decimal = Field(sa_column=_rate_column())

    sort_order: int = Field(default=0)
