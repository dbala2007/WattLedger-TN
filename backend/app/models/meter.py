"""The Meter table: one row per physical EB/solar meter being tracked."""

import uuid
from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel

from app.models.enums import SolarMode


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Meter(SQLModel, table=True):
    # Using a UUID string (not an auto-increment int) as the primary key.
    # This matters later: when multiple devices sync to a shared database
    # (PRP Phase 4/5), IDs generated offline on different devices must not
    # collide. Deciding this now avoids a painful ID migration later.
    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # Which logged-in user owns this meter (CLAUDE.md Phase 3). Every
    # reading/billing lookup is reached through the meter, so scoping
    # ownership here is enough to keep one user's data invisible to
    # another - see app.services.meter_service.get_meter.
    user_id: str = Field(index=True, foreign_key="user.id")

    # The TNPDCL/EB meter number as the user knows it. Kept as an internal
    # id-referenced field rather than the primary key, since meter numbers
    # are not guaranteed globally unique across providers (PRP FR-001).
    meter_number: str = Field(index=True)

    display_name: str | None = None
    solar_mode: SolarMode = Field(default=SolarMode.NONE)
    active: bool = Field(default=True)

    # The start date of *some* past billing cycle for this meter. The
    # billing-cycle engine repeatedly steps forward/back from this anchor by
    # cycle_length_months to find whichever cycle window contains a given
    # date - it does not assume cycles start on the 1st of an odd/even month
    # (PRP.md section 6).
    billing_cycle_reference_date: date | None = None
    cycle_length_months: int = Field(default=2)

    # User-correctable assessment dates (PRP.md section 6): the last time
    # TNPDCL actually issued a bill, and when the next one is expected.
    last_assessment_date: date | None = None
    next_expected_assessment_date: date | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
