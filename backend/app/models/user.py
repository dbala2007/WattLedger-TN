"""The User table: one row per person who can log in to WattLedger TN.

Every Meter (and everything hanging off it - readings, billing) belongs to
exactly one user, so different households/logins never see each other's
data even though they share the same backend and database (CLAUDE.md
Phase 3). Tariff plans stay unscoped - they represent shared TN government
tariff schedules, not per-user data.
"""

import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # Used as the login name. Stored lowercase so lookups are
    # case-insensitive without needing a separate index/collation.
    email: str = Field(index=True, unique=True)

    # Never store the raw password - only the bcrypt hash (app/core/security.py).
    hashed_password: str

    # Self-service "forgot password" (app/domain/auth.py): two fixed
    # questions, each with its own hashed answer - never stored in plain
    # text, same as the password itself.
    security_question_1: str
    security_answer_1_hash: str
    security_question_2: str
    security_answer_2_hash: str

    created_at: datetime = Field(default_factory=_utcnow)
