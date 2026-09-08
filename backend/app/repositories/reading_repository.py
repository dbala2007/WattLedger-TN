"""Database access for MeterReading rows."""

from datetime import date

from sqlmodel import Session, select

from app.models.reading import MeterReading


def get(session: Session, reading_id: str) -> MeterReading | None:
    return session.get(MeterReading, reading_id)


def get_by_meter_and_date(session: Session, meter_id: str, reading_date: date) -> MeterReading | None:
    statement = select(MeterReading).where(
        MeterReading.meter_id == meter_id,
        MeterReading.reading_date == reading_date,
    )
    return session.exec(statement).first()


def list_for_meter(
    session: Session,
    meter_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[MeterReading]:
    """All readings for a meter, oldest first.

    Oldest-first ordering matters: this is what makes chronological balance
    recalculation (see domain.readings.recalculate_chain) correct, rather
    than relying on the order rows happened to be inserted in.
    """
    statement = select(MeterReading).where(MeterReading.meter_id == meter_id)
    if start_date is not None:
        statement = statement.where(MeterReading.reading_date >= start_date)
    if end_date is not None:
        statement = statement.where(MeterReading.reading_date <= end_date)
    statement = statement.order_by(MeterReading.reading_date.asc())
    return list(session.exec(statement))


def save_all(session: Session, readings: list[MeterReading]) -> None:
    """Persist multiple readings (e.g. after a recalculation pass) in one commit."""
    for reading in readings:
        session.add(reading)
    session.commit()


def create(session: Session, reading: MeterReading) -> MeterReading:
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


def delete(session: Session, reading: MeterReading) -> None:
    session.delete(reading)
    session.commit()
