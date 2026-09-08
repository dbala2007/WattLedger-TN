"""Response shapes for billing-cycle and bill-estimate endpoints."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class BillingCycleRead(BaseModel):
    meter_id: str
    period_start: date
    period_end: date


class SlabChargeRead(BaseModel):
    rule_group: str
    from_unit: Decimal
    to_unit: Decimal | None
    rate_per_unit: Decimal
    units_charged: Decimal
    amount: Decimal


class BillEstimateRead(BaseModel):
    meter_id: str
    period_start: date
    period_end: date
    total_eb_units: Decimal
    total_solar_units: Decimal
    reading_count: int
    note: str | None = None

    # Everything below is None until there is at least one reading in the
    # cycle. CLAUDE.md section 5 requires every field of the breakdown to be
    # shown, never just a final total.
    rule_group: str | None = None
    free_units_applied: Decimal | None = None
    chargeable_units: Decimal | None = None
    slab_charges: list[SlabChargeRead] = []
    fixed_charge: Decimal | None = None
    total_estimated_amount: Decimal | None = None
    tariff_plan_id: str | None = None
    tariff_plan_name: str | None = None
    tariff_effective_from: date | None = None
    tariff_source_reference: str | None = None
