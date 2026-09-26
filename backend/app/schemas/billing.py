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
    solar_units_offset: Decimal | None = None
    slab_charges: list[SlabChargeRead] = []
    fixed_charge: Decimal | None = None
    total_estimated_amount: Decimal | None = None
    tariff_plan_id: str | None = None
    tariff_plan_name: str | None = None
    tariff_effective_from: date | None = None
    tariff_source_reference: str | None = None


class BillingAssessmentWrite(BaseModel):
    """Body for recording or editing a meter reader visit. Used for both
    POST (create) and PUT (full replace), so leaving official_bill_amount
    or notes out on a PUT clears them.
    """

    assessed_on: date
    official_bill_amount: Decimal | None = None
    notes: str | None = None


class BillingAssessmentRead(BaseModel):
    id: str
    meter_id: str
    assessed_on: date
    official_bill_amount: Decimal | None
    notes: str | None

    model_config = {"from_attributes": True}


class PastCycleBillRead(BaseModel):
    """One completed cycle: the app's estimate plus the official bill
    (entered on the closing visit) and the difference between them.
    """

    opening_assessment_id: str
    closing_assessment_id: str
    official_bill_amount: Decimal | None
    difference: Decimal | None
    estimate: BillEstimateRead
