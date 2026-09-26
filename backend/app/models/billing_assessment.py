"""The BillingAssessment table: one row per official TNPDCL assessment
(the day the meter reader actually visited and a bill was raised).

Consecutive assessments define the household's real billing cycles:
the cycle closed by an assessment on date X runs from the previous
assessment's date up to the day before X (see
app.domain.billing_cycles.completed_cycles_from_assessments).

Only user-entered facts are stored here (the date, the official bill
amount, notes). Consumed units and the estimated amount are always
recalculated from the readings, so editing a historical reading
automatically updates that cycle's history too - see
docs/decisions/0007-billing-assessment-history.md.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BillingAssessment(SQLModel, table=True):
    # One meter reader visit per meter per day - recording the same date
    # twice would create a zero-length cycle.
    __table_args__ = (UniqueConstraint("meter_id", "assessed_on", name="uq_billing_assessment_date"),)

    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    meter_id: str = Field(foreign_key="meter.id", index=True)

    # The local calendar date (Asia/Kolkata) of the meter reader's visit.
    assessed_on: date = Field(index=True)

    # What TNPDCL actually charged for the cycle that ends at this visit,
    # if the user entered it - lets the app compare estimate vs actual.
    # Numeric(12, 2) because it's rupees and paise, not kWh.
    official_bill_amount: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 2), nullable=True))

    notes: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
