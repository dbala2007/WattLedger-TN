"""Database access for DeviceSession rows."""

from datetime import datetime

from sqlmodel import Session, select

from app.models.device_session import DeviceSession


def get_by_token_hash(session: Session, token_hash: str) -> DeviceSession | None:
    statement = select(DeviceSession).where(DeviceSession.token_hash == token_hash)
    return session.exec(statement).first()


def save(session: Session, device_session: DeviceSession) -> DeviceSession:
    session.add(device_session)
    session.commit()
    session.refresh(device_session)
    return device_session


def revoke_all_for_user(session: Session, user_id: str, revoked_at: datetime) -> int:
    """Marks every still-active session of a user as revoked; returns how many."""
    statement = select(DeviceSession).where(DeviceSession.user_id == user_id, DeviceSession.revoked_at == None)  # noqa: E711
    active = list(session.exec(statement))
    for device_session in active:
        device_session.revoked_at = revoked_at
        session.add(device_session)
    session.commit()
    return len(active)
