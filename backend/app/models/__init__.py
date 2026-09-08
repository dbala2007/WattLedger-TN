"""Import all models here so SQLModel.metadata knows about every table
before create_db_and_tables() runs.
"""

from app.models.enums import BillingFrequency, SolarMode
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.models.tariff import SubsidyRule, TariffPlan, TariffSlab
from app.models.user import User

__all__ = [
    "SolarMode",
    "BillingFrequency",
    "Meter",
    "MeterReading",
    "TariffPlan",
    "TariffSlab",
    "SubsidyRule",
    "User",
]
