"""Request/response shapes for the readings API.

Note there is no eb_balance/solar_balance field on ReadingCreate - per
CLAUDE.md, balances are calculated server-side and must never be trusted
from the client.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ReadingCreate(BaseModel):
    reading_date: date
    eb_units: Decimal
    solar_units: Decimal | None = None
    notes: str | None = None


class ReadingUpdate(BaseModel):
    eb_units: Decimal | None = None
    solar_units: Decimal | None = None
    notes: str | None = None


class ReadingRead(BaseModel):
    id: str
    meter_id: str
    reading_date: date
    eb_units: Decimal
    eb_balance: Decimal | None
    solar_units: Decimal | None
    solar_balance: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
