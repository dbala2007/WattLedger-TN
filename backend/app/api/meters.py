"""HTTP endpoints for managing meters."""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.meter import MeterCreate, MeterRead, MeterUpdate
from app.services import meter_service

router = APIRouter(prefix="/meters", tags=["meters"])


@router.post("", response_model=MeterRead, status_code=status.HTTP_201_CREATED)
def create_meter(
    payload: MeterCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MeterRead:
    return meter_service.create_meter(
        session,
        user_id=current_user.id,
        meter_number=payload.meter_number,
        display_name=payload.display_name,
        solar_mode=payload.solar_mode,
        billing_cycle_reference_date=payload.billing_cycle_reference_date,
        cycle_length_months=payload.cycle_length_months,
    )


@router.get("", response_model=list[MeterRead])
def list_meters(
    active_only: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[MeterRead]:
    return meter_service.list_meters(session, current_user.id, active_only=active_only)


@router.get("/{meter_id}", response_model=MeterRead)
def get_meter(
    meter_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MeterRead:
    return meter_service.get_meter(session, meter_id, current_user.id)


@router.patch("/{meter_id}", response_model=MeterRead)
def update_meter(
    meter_id: str,
    payload: MeterUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MeterRead:
    return meter_service.update_meter(
        session,
        meter_id,
        current_user.id,
        display_name=payload.display_name,
        solar_mode=payload.solar_mode,
        active=payload.active,
        billing_cycle_reference_date=payload.billing_cycle_reference_date,
        cycle_length_months=payload.cycle_length_months,
        last_assessment_date=payload.last_assessment_date,
        next_expected_assessment_date=payload.next_expected_assessment_date,
    )
