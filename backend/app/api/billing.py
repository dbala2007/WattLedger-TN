"""HTTP endpoints for the current billing cycle and bill estimate."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.billing import BillEstimateRead, BillingCycleRead, SlabChargeRead
from app.services import billing_service

router = APIRouter(tags=["billing"])


@router.get("/meters/{meter_id}/billing-cycle/current", response_model=BillingCycleRead)
def get_current_billing_cycle(
    meter_id: str,
    as_of: date | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BillingCycleRead:
    window = billing_service.get_current_billing_cycle(session, meter_id, current_user.id, as_of_date=as_of)
    return BillingCycleRead(
        meter_id=window.meter_id, period_start=window.period_start, period_end=window.period_end
    )


@router.get("/meters/{meter_id}/bill-estimate", response_model=BillEstimateRead)
def get_bill_estimate(
    meter_id: str,
    as_of: date | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BillEstimateRead:
    estimate = billing_service.estimate_current_bill(session, meter_id, current_user.id, as_of_date=as_of)
    breakdown = estimate.breakdown

    return BillEstimateRead(
        meter_id=estimate.meter_id,
        period_start=estimate.period_start,
        period_end=estimate.period_end,
        total_eb_units=estimate.total_eb_units,
        total_solar_units=estimate.total_solar_units,
        reading_count=estimate.reading_count,
        note=estimate.note,
        rule_group=breakdown.rule_group if breakdown else None,
        free_units_applied=breakdown.free_units_applied if breakdown else None,
        chargeable_units=breakdown.chargeable_units if breakdown else None,
        slab_charges=[SlabChargeRead(**vars(sc)) for sc in breakdown.slab_charges] if breakdown else [],
        fixed_charge=breakdown.fixed_charge if breakdown else None,
        total_estimated_amount=breakdown.total_estimated_amount if breakdown else None,
        tariff_plan_id=breakdown.tariff_plan_id if breakdown else None,
        tariff_plan_name=breakdown.tariff_plan_name if breakdown else None,
        tariff_effective_from=breakdown.tariff_effective_from if breakdown else None,
        tariff_source_reference=breakdown.tariff_source_reference if breakdown else None,
    )
