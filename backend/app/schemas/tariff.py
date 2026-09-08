"""Request/response shapes for the tariff configuration API.

A tariff plan is created together with its subsidy rules and slabs in one
request, since a plan without any rule groups isn't usable - this avoids
the API allowing a half-configured plan to exist even briefly.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import BillingFrequency


class SubsidyRuleCreate(BaseModel):
    rule_name: str
    consumption_min: Decimal
    consumption_max: Decimal | None = None
    free_units: Decimal
    effective_from: date
    effective_to: date | None = None


class TariffSlabCreate(BaseModel):
    rule_group: str
    from_unit: Decimal
    to_unit: Decimal | None = None
    rate_per_unit: Decimal
    sort_order: int = 0


class TariffPlanCreate(BaseModel):
    name: str
    provider: str = "TANGEDCO"
    consumer_category: str = "DOMESTIC"
    effective_from: date
    effective_to: date | None = None
    billing_frequency: BillingFrequency = BillingFrequency.BI_MONTHLY
    fixed_charge: Decimal = Decimal("0")
    source_reference: str
    active: bool = True
    subsidy_rules: list[SubsidyRuleCreate]
    slabs: list[TariffSlabCreate]


class SubsidyRuleRead(BaseModel):
    id: str
    rule_name: str
    consumption_min: Decimal
    consumption_max: Decimal | None
    free_units: Decimal
    effective_from: date
    effective_to: date | None

    model_config = {"from_attributes": True}


class TariffSlabRead(BaseModel):
    id: str
    rule_group: str
    from_unit: Decimal
    to_unit: Decimal | None
    rate_per_unit: Decimal
    sort_order: int

    model_config = {"from_attributes": True}


class TariffPlanRead(BaseModel):
    id: str
    name: str
    provider: str
    consumer_category: str
    effective_from: date
    effective_to: date | None
    billing_frequency: BillingFrequency
    fixed_charge: Decimal
    source_reference: str
    active: bool
    subsidy_rules: list[SubsidyRuleRead] = []
    slabs: list[TariffSlabRead] = []

    model_config = {"from_attributes": True}
