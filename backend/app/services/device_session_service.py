"""'Keep me logged in' - remembered devices.

When the user ticks "Keep me logged in", the device is given a refresh
token (see app.models.device_session). Later, when its short-lived access
token has expired, the device calls refresh_access_token() with it and
gets a new access token without asking for the password.
"""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import create_access_token, generate_refresh_token, hash_refresh_token
from app.domain.errors import InvalidCredentialsError
from app.models.device_session import DeviceSession
from app.repositories import device_session_repository

logger = get_logger(__name__)

_EXPIRED_MESSAGE = "Your saved login has expired or was signed out. Please log in again."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """SQLite (and PostgreSQL's default timestamp column) hand datetimes
    back without a timezone even though they were saved as UTC. Mark them
    as UTC again so they can be compared with _now().
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def create_device_session(session: Session, *, user_id: str, device_name: str | None = None) -> str:
    """Remember this device. Returns the refresh token - the only time the
    raw secret exists on the server; just its hash is saved.
    """
    refresh_token = generate_refresh_token()
    now = _now()
    device_session_repository.save(
        session,
        DeviceSession(
            user_id=user_id,
            token_hash=hash_refresh_token(refresh_token),
            device_name=(device_name or "").strip()[:100] or None,
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(days=settings.remember_me_days),
        ),
    )
    logger.info("Remembered a new device (%s) for user %s", device_name or "unnamed", user_id)
    return refresh_token


def refresh_access_token(session: Session, *, refresh_token: str) -> str:
    """Trade a remembered device's refresh token for a new access token.

    Raises InvalidCredentialsError (HTTP 401) if the token is unknown,
    revoked, or unused for too long - the device must then log in again.
    Each successful use extends the session by settings.remember_me_days.
    """
    device_session = device_session_repository.get_by_token_hash(session, hash_refresh_token(refresh_token))
    now = _now()
    if (
        device_session is None
        or device_session.revoked_at is not None
        or _as_utc(device_session.expires_at) <= now
    ):
        raise InvalidCredentialsError(_EXPIRED_MESSAGE)

    device_session.last_used_at = now
    device_session.expires_at = now + timedelta(days=settings.remember_me_days)
    device_session_repository.save(session, device_session)
    return create_access_token(device_session.user_id)


def revoke_device_session(session: Session, *, refresh_token: str) -> None:
    """Log this one device out. Unknown or already-revoked tokens are
    ignored, so logging out twice (or offline, then again) is harmless.
    """
    device_session = device_session_repository.get_by_token_hash(session, hash_refresh_token(refresh_token))
    if device_session is None or device_session.revoked_at is not None:
        return
    device_session.revoked_at = _now()
    device_session_repository.save(session, device_session)
    logger.info("Device session %s logged out", device_session.id)


def revoke_all_device_sessions(session: Session, *, user_id: str) -> None:
    """Sign every remembered device out - used after a password reset, so
    someone who had the old password can't stay logged in on another device.
    """
    count = device_session_repository.revoke_all_for_user(session, user_id, _now())
    if count:
        logger.info("Revoked %s remembered device(s) for user %s", count, user_id)
