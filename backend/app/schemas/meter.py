"""Request/response shapes for the /meters API - kept separate from the
Meter table model so the database schema can change without automatically
changing the public API, and vice versa.
"""

from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import SolarMode


class MeterCreate(BaseModel):
    meter_number: str
    display_name: str | None = None
    solar_mode: SolarMode = SolarMode.NONE
    billing_cycle_reference_date: date | None = None
    cycle_length_months: int = 2


class MeterUpdate(BaseModel):
    """All fields optional - only the ones provided are changed (PATCH semantics)."""

    display_name: str | None = None
    solar_mode: SolarMode | None = None
    active: bool | None = None
    billing_cycle_reference_date: date | None = None
    cycle_length_months: int | None = None
    last_assessment_date: date | None = None
    next_expected_assessment_date: date | None = None


class MeterRead(BaseModel):
    id: str
    meter_number: str
    display_name: str | None
    solar_mode: SolarMode
    active: bool
    billing_cycle_reference_date: date | None
    cycle_length_months: int
    last_assessment_date: date | None
    next_expected_assessment_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
