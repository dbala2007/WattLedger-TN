"""Orchestrates daily reading entry, edit, and delete.

This is where domain rules (app.domain.readings) and persistence
(app.repositories) come together. Every write path here re-runs the full
chronological recalculation, so balances are always derived from actual
reading order - never from insertion order - satisfying CLAUDE.md's rule
that backdated inserts/edits/deletes must recalculate affected balances.

Recalculating the whole meter's history on every write is intentionally the
simple approach: household reading volume is low (NFR-004), so the extra
work is negligible, and "always recompute everything" is far less
bug-prone than trying to figure out exactly which single row is affected.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Session

from app.core.logging import get_logger
from app.domain.errors import NotFoundError
from app.domain.readings import ReadingValidationError, recalculate_chain, validate_reading
from app.models.reading import MeterReading
from app.repositories import reading_repository
from app.services import meter_service

logger = get_logger(__name__)


def _find_previous(readings_sorted_ascending: list[MeterReading], reading_date: date) -> MeterReading | None:
    """Last reading strictly before reading_date, given an ascending list."""
    previous: MeterReading | None = None
    for reading in readings_sorted_ascending:
        if reading.reading_date < reading_date:
            previous = reading
        else:
            break
    return previous


def create_reading(
    session: Session,
    *,
    meter_id: str,
    user_id: str,
    reading_date: date,
    eb_units: Decimal,
    solar_units: Decimal | None = None,
    notes: str | None = None,
) -> MeterReading:
    meter = meter_service.get_meter(session, meter_id, user_id)  # raises NotFoundError if missing/not owned

    existing = reading_repository.get_by_meter_and_date(session, meter_id, reading_date)
    all_readings = reading_repository.list_for_meter(session, meter_id)
    previous = _find_previous(all_readings, reading_date)

    errors = validate_reading(
        solar_mode=meter.solar_mode,
        eb_units=eb_units,
        solar_units=solar_units,
        previous_eb_units=previous.eb_units if previous else None,
        previous_solar_units=previous.solar_units if previous else None,
        date_already_has_reading=existing is not None,
    )
    if errors:
        raise ReadingValidationError(errors)

    new_reading = MeterReading(
        meter_id=meter_id,
        reading_date=reading_date,
        eb_units=eb_units,
        solar_units=solar_units,
        notes=notes,
    )

    all_readings.append(new_reading)
    all_readings.sort(key=lambda r: r.reading_date)
    recalculate_chain(all_readings)

    reading_repository.save_all(session, all_readings)
    session.refresh(new_reading)

    logger.info(
        "Created reading for meter %s on %s (eb_balance=%s, solar_balance=%s)",
        meter_id, reading_date, new_reading.eb_balance, new_reading.solar_balance,
    )
    return new_reading


def update_reading(
    session: Session,
    reading_id: str,
    user_id: str,
    *,
    eb_units: Decimal | None = None,
    solar_units: Decimal | None = None,
    notes: str | None = None,
) -> MeterReading:
    reading = reading_repository.get(session, reading_id)
    if reading is None:
        raise NotFoundError(f"Reading {reading_id} not found.")

    meter = meter_service.get_meter(session, reading.meter_id, user_id)

    new_eb_units = eb_units if eb_units is not None else reading.eb_units
    new_solar_units = solar_units if solar_units is not None else reading.solar_units

    all_readings = reading_repository.list_for_meter(session, reading.meter_id)
    other_readings = [r for r in all_readings if r.id != reading.id]
    previous = _find_previous(other_readings, reading.reading_date)

    errors = validate_reading(
        solar_mode=meter.solar_mode,
        eb_units=new_eb_units,
        solar_units=new_solar_units,
        previous_eb_units=previous.eb_units if previous else None,
        previous_solar_units=previous.solar_units if previous else None,
        date_already_has_reading=False,  # editing the same row/date is expected
    )
    if errors:
        raise ReadingValidationError(errors)

    reading.eb_units = new_eb_units
    reading.solar_units = new_solar_units
    if notes is not None:
        reading.notes = notes
    reading.updated_at = datetime.now(timezone.utc)

    # `all_readings` contains this same `reading` object (SQLAlchemy's
    # identity map returns the same Python instance for the same row within
    # one session), so the edits above are already reflected when we
    # recalculate the chain.
    recalculate_chain(all_readings)
    reading_repository.save_all(session, all_readings)
    session.refresh(reading)

    logger.info("Updated reading %s for meter %s", reading_id, reading.meter_id)
    return reading


def delete_reading(session: Session, reading_id: str, user_id: str) -> None:
    reading = reading_repository.get(session, reading_id)
    if reading is None:
        raise NotFoundError(f"Reading {reading_id} not found.")

    meter_service.get_meter(session, reading.meter_id, user_id)  # ownership check

    meter_id = reading.meter_id
    reading_repository.delete(session, reading)

    remaining = reading_repository.list_for_meter(session, meter_id)
    recalculate_chain(remaining)
    reading_repository.save_all(session, remaining)

    logger.info("Deleted reading %s for meter %s", reading_id, meter_id)


def list_readings(
    session: Session,
    meter_id: str,
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[MeterReading]:
    meter_service.get_meter(session, meter_id, user_id)  # raises NotFoundError if missing/not owned
    return reading_repository.list_for_meter(session, meter_id, start_date, end_date)
