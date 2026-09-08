"""HTTP endpoints for daily readings: create, list, edit, delete."""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.reading import ReadingCreate, ReadingRead, ReadingUpdate
from app.services import reading_service

router = APIRouter(tags=["readings"])


@router.post(
    "/meters/{meter_id}/readings",
    response_model=ReadingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_reading(
    meter_id: str,
    payload: ReadingCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReadingRead:
    return reading_service.create_reading(
        session,
        meter_id=meter_id,
        user_id=current_user.id,
        reading_date=payload.reading_date,
        eb_units=payload.eb_units,
        solar_units=payload.solar_units,
        notes=payload.notes,
    )


@router.get("/meters/{meter_id}/readings", response_model=list[ReadingRead])
def list_readings(
    meter_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ReadingRead]:
    return reading_service.list_readings(session, meter_id, current_user.id, start_date, end_date)


@router.patch("/readings/{reading_id}", response_model=ReadingRead)
def update_reading(
    reading_id: str,
    payload: ReadingUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReadingRead:
    return reading_service.update_reading(
        session,
        reading_id,
        current_user.id,
        eb_units=payload.eb_units,
        solar_units=payload.solar_units,
        notes=payload.notes,
    )


@router.delete("/readings/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(
    reading_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    reading_service.delete_reading(session, reading_id, current_user.id)
