"""The MeterReading table: one row per daily cumulative reading.

eb_balance and solar_balance are stored (not computed on every read) so that
history queries stay fast, but they are always written by the domain/service
layer from the chronologically-previous reading - never typed by the user
directly (see CLAUDE.md section 3, "Important rule").
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Numeric(12, 3): up to 12 total digits, 3 after the decimal point. Using a
# fixed-point database type (not float) avoids binary floating-point rounding
# errors when subtracting readings - important since this feeds billing math.
class MeterReading(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("meter_id", "reading_date", name="uq_meter_reading_date"),)

    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    meter_id: str = Field(foreign_key="meter.id", index=True)
    reading_date: date = Field(index=True)

    eb_units: Decimal = Field(sa_column=Column(Numeric(12, 3), nullable=False))
    eb_balance: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 3), nullable=True))

    solar_units: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 3), nullable=True))
    solar_balance: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 3), nullable=True))

    notes: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
