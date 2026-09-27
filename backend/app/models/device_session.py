"""The DeviceSession table: one row per device where the user ticked
"Keep me logged in" (CLAUDE.md section 10, "DeviceSession / RefreshToken").

The device keeps a long-lived random secret (the "refresh token") in its
secure storage and trades it for a fresh short-lived access token whenever
the old one expires - so the user is not asked for their password again.
Only a SHA-256 hash of that secret is stored here, never the secret
itself, so a leaked database cannot be used to log in as anyone.

A session ends when it is revoked (logout on that device, or a password
reset, which revokes every device) or when it goes unused for
settings.remember_me_days - every successful refresh pushes expires_at
forward again.
"""

import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeviceSession(SQLModel, table=True):
    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id")

    # SHA-256 hex of the refresh token - looked up on every refresh.
    token_hash: str = Field(index=True, unique=True)

    # e.g. "Windows", "Android", "Web" - lets a future "your devices"
    # screen show where the user is logged in.
    device_name: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    last_used_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime
    revoked_at: datetime | None = None
