"""HTTP endpoints for billing cycles, bill estimates, and the history of
official assessments (meter reader visits) that defines past cycles.
"""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.billing import (
    BillEstimateRead,
    BillingAssessmentRead,
    BillingAssessmentWrite,
    BillingCycleRead,
    PastCycleBillRead,
    SlabChargeRead,
)
from app.services import billing_assessment_service, billing_service

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
    return _to_estimate_read(estimate)


@router.get("/meters/{meter_id}/billing-history", response_model=list[PastCycleBillRead])
def get_billing_history(
    meter_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[PastCycleBillRead]:
    """Completed cycles (newest first), one between each pair of recorded
    assessments, each with its full bill breakdown.
    """
    return [
        PastCycleBillRead(
            opening_assessment_id=cycle.opening_assessment_id,
            closing_assessment_id=cycle.closing_assessment_id,
            official_bill_amount=cycle.official_bill_amount,
            difference=cycle.difference,
            estimate=_to_estimate_read(cycle.estimate),
        )
        for cycle in billing_service.get_billing_history(session, meter_id, current_user.id)
    ]


@router.get("/meters/{meter_id}/assessments", response_model=list[BillingAssessmentRead])
def list_assessments(
    meter_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[BillingAssessmentRead]:
    return billing_assessment_service.list_assessments(session, meter_id, current_user.id)


@router.post(
    "/meters/{meter_id}/assessments", response_model=BillingAssessmentRead, status_code=status.HTTP_201_CREATED
)
def create_assessment(
    meter_id: str,
    payload: BillingAssessmentWrite,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BillingAssessmentRead:
    return billing_assessment_service.create_assessment(
        session, meter_id=meter_id, user_id=current_user.id, **payload.model_dump()
    )


@router.put("/meters/{meter_id}/assessments/{assessment_id}", response_model=BillingAssessmentRead)
def update_assessment(
    meter_id: str,
    assessment_id: str,
    payload: BillingAssessmentWrite,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BillingAssessmentRead:
    return billing_assessment_service.update_assessment(
        session, meter_id=meter_id, assessment_id=assessment_id, user_id=current_user.id, **payload.model_dump()
    )


@router.delete("/meters/{meter_id}/assessments/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    meter_id: str,
    assessment_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    billing_assessment_service.delete_assessment(
        session, meter_id=meter_id, assessment_id=assessment_id, user_id=current_user.id
    )


def _to_estimate_read(estimate: billing_service.CurrentBillEstimate) -> BillEstimateRead:
    """Flatten a service-layer estimate into the API response shape.
    Shared by the current-cycle estimate and every history entry.
    """
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
        solar_units_offset=breakdown.solar_units_offset if breakdown else None,
        slab_charges=[SlabChargeRead(**vars(sc)) for sc in breakdown.slab_charges] if breakdown else [],
        fixed_charge=breakdown.fixed_charge if breakdown else None,
        total_estimated_amount=breakdown.total_estimated_amount if breakdown else None,
        tariff_plan_id=breakdown.tariff_plan_id if breakdown else None,
        tariff_plan_name=breakdown.tariff_plan_name if breakdown else None,
        tariff_effective_from=breakdown.tariff_effective_from if breakdown else None,
        tariff_source_reference=breakdown.tariff_source_reference if breakdown else None,
    )
