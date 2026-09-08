"""Orchestrates meter creation/lookup: validates input, then delegates to the
meter repository for persistence.
"""

from datetime import date, datetime, timezone

from sqlmodel import Session

from app.core.logging import get_logger
from app.domain.errors import NotFoundError
from app.models.enums import SolarMode
from app.models.meter import Meter
from app.repositories import meter_repository

logger = get_logger(__name__)


def create_meter(
    session: Session,
    *,
    user_id: str,
    meter_number: str,
    display_name: str | None = None,
    solar_mode: SolarMode = SolarMode.NONE,
    billing_cycle_reference_date: date | None = None,
    cycle_length_months: int = 2,
) -> Meter:
    if not meter_number or not meter_number.strip():
        raise ValueError("Meter number is required.")
    if cycle_length_months <= 0:
        raise ValueError("cycle_length_months must be a positive number of months.")

    meter = Meter(
        user_id=user_id,
        meter_number=meter_number.strip(),
        display_name=display_name,
        solar_mode=solar_mode,
        billing_cycle_reference_date=billing_cycle_reference_date,
        cycle_length_months=cycle_length_months,
    )
    created = meter_repository.create(session, meter)
    logger.info("Created meter %s (meter_number=%s)", created.id, created.meter_number)
    return created


def get_meter(session: Session, meter_id: str, user_id: str) -> Meter:
    """Raises NotFoundError both when the meter doesn't exist at all and
    when it belongs to a different user - the caller shouldn't be able to
    tell those two cases apart (CLAUDE.md section 14: authorization checks
    on every household/meter resource).
    """
    meter = meter_repository.get(session, meter_id)
    if meter is None or meter.user_id != user_id:
        raise NotFoundError(f"Meter {meter_id} not found.")
    return meter


def list_meters(session: Session, user_id: str, active_only: bool = False) -> list[Meter]:
    return meter_repository.list_all(session, user_id, active_only=active_only)


def update_meter(
    session: Session,
    meter_id: str,
    user_id: str,
    *,
    display_name: str | None = None,
    solar_mode: SolarMode | None = None,
    active: bool | None = None,
    billing_cycle_reference_date: date | None = None,
    cycle_length_months: int | None = None,
    last_assessment_date: date | None = None,
    next_expected_assessment_date: date | None = None,
) -> Meter:
    meter = get_meter(session, meter_id, user_id)

    if cycle_length_months is not None:
        if cycle_length_months <= 0:
            raise ValueError("cycle_length_months must be a positive number of months.")
        meter.cycle_length_months = cycle_length_months
    if display_name is not None:
        meter.display_name = display_name
    if solar_mode is not None:
        meter.solar_mode = solar_mode
    if active is not None:
        meter.active = active
    if billing_cycle_reference_date is not None:
        meter.billing_cycle_reference_date = billing_cycle_reference_date
    if last_assessment_date is not None:
        meter.last_assessment_date = last_assessment_date
    if next_expected_assessment_date is not None:
        meter.next_expected_assessment_date = next_expected_assessment_date

    meter.updated_at = datetime.now(timezone.utc)
    updated = meter_repository.update(session, meter)
    logger.info("Updated meter %s", meter_id)
    return updated
