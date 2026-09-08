"""Database access for Meter rows.

Repositories only know how to fetch/save data - they contain no business
rules. That logic lives in app/domain and app/services instead.
"""

from sqlmodel import Session, select

from app.models.meter import Meter


def get(session: Session, meter_id: str) -> Meter | None:
    return session.get(Meter, meter_id)


def list_all(session: Session, user_id: str, active_only: bool = False) -> list[Meter]:
    statement = select(Meter).where(Meter.user_id == user_id)
    if active_only:
        statement = statement.where(Meter.active == True)  # noqa: E712
    return list(session.exec(statement))


def create(session: Session, meter: Meter) -> Meter:
    session.add(meter)
    session.commit()
    session.refresh(meter)
    return meter


def update(session: Session, meter: Meter) -> Meter:
    session.add(meter)
    session.commit()
    session.refresh(meter)
    return meter
