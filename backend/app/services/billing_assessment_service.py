"""Orchestrates recording, editing and deleting official TNPDCL assessments
(meter reader visits) for a meter.

The assessment history is the single source of truth for a meter's real
cycle boundaries. Meter.last_assessment_date is kept as a copy of the
latest visit date (so get_current_cycle_for_meter and existing clients keep
working unchanged) and is refreshed by _sync_meter after every change here.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Session

from app.core.logging import get_logger
from app.core.timezone import today_local
from app.domain.errors import NotFoundError
from app.models.billing_assessment import BillingAssessment
from app.models.meter import Meter
from app.repositories import billing_assessment_repository, meter_repository
from app.services import meter_service

logger = get_logger(__name__)


def _validate(session: Session, meter_id: str, assessed_on: date, official_bill_amount: Decimal | None,
              existing_id: str | None = None) -> None:
    """Raises ValueError (HTTP 400) for input that can't be saved."""
    if assessed_on > today_local():
        raise ValueError("Assessment date cannot be in the future.")
    if official_bill_amount is not None and official_bill_amount < 0:
        raise ValueError("Official bill amount cannot be negative.")

    clash = billing_assessment_repository.get_by_meter_and_date(session, meter_id, assessed_on)
    if clash is not None and clash.id != existing_id:
        raise ValueError(f"An assessment is already recorded on {assessed_on.isoformat()} for this meter.")


def _sync_meter(session: Session, meter: Meter) -> None:
    """Point meter.last_assessment_date at the latest recorded visit (or
    None if there are none left), so the current cycle always starts at
    the most recent real visit.

    A next_expected_assessment_date that is no longer after the latest
    visit described the cycle that has just been closed, so it is cleared
    - the cycle-length placeholder is used until the user enters a new one.
    """
    assessments = billing_assessment_repository.list_for_meter(session, meter.id)
    meter.last_assessment_date = assessments[-1].assessed_on if assessments else None

    if (
        meter.last_assessment_date is not None
        and meter.next_expected_assessment_date is not None
        and meter.next_expected_assessment_date <= meter.last_assessment_date
    ):
        meter.next_expected_assessment_date = None

    meter.updated_at = datetime.now(timezone.utc)
    meter_repository.update(session, meter)


def list_assessments(session: Session, meter_id: str, user_id: str) -> list[BillingAssessment]:
    meter_service.get_meter(session, meter_id, user_id)  # ownership check
    return billing_assessment_repository.list_for_meter(session, meter_id)


def create_assessment(
    session: Session,
    *,
    meter_id: str,
    user_id: str,
    assessed_on: date,
    official_bill_amount: Decimal | None = None,
    notes: str | None = None,
) -> BillingAssessment:
    meter = meter_service.get_meter(session, meter_id, user_id)
    _validate(session, meter_id, assessed_on, official_bill_amount)

    assessment = billing_assessment_repository.save(
        session,
        BillingAssessment(
            meter_id=meter_id, assessed_on=assessed_on, official_bill_amount=official_bill_amount, notes=notes
        ),
    )
    _sync_meter(session, meter)
    logger.info("Recorded assessment %s for meter %s on %s", assessment.id, meter_id, assessed_on)
    return assessment


def _get_owned_assessment(session: Session, meter_id: str, assessment_id: str, user_id: str):
    meter = meter_service.get_meter(session, meter_id, user_id)
    assessment = billing_assessment_repository.get(session, assessment_id)
    # Same "not found" for missing and someone-else's rows (see meter_service.get_meter).
    if assessment is None or assessment.meter_id != meter_id:
        raise NotFoundError(f"Assessment {assessment_id} not found.")
    return meter, assessment


def update_assessment(
    session: Session,
    *,
    meter_id: str,
    assessment_id: str,
    user_id: str,
    assessed_on: date,
    official_bill_amount: Decimal | None,
    notes: str | None,
) -> BillingAssessment:
    """Full replace (PUT semantics) - so clearing the official amount or
    notes back to empty is possible, which PATCH-style "None means
    unchanged" could not express.
    """
    meter, assessment = _get_owned_assessment(session, meter_id, assessment_id, user_id)
    _validate(session, meter_id, assessed_on, official_bill_amount, existing_id=assessment_id)

    assessment.assessed_on = assessed_on
    assessment.official_bill_amount = official_bill_amount
    assessment.notes = notes
    assessment.updated_at = datetime.now(timezone.utc)
    assessment = billing_assessment_repository.save(session, assessment)
    _sync_meter(session, meter)
    logger.info("Updated assessment %s for meter %s", assessment_id, meter_id)
    return assessment


def delete_assessment(session: Session, *, meter_id: str, assessment_id: str, user_id: str) -> None:
    meter, assessment = _get_owned_assessment(session, meter_id, assessment_id, user_id)
    billing_assessment_repository.delete(session, assessment)
    _sync_meter(session, meter)
    logger.info("Deleted assessment %s for meter %s", assessment_id, meter_id)
