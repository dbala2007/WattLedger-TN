"""Shared enum types used across models, schemas, and domain logic."""

from enum import Enum


class SolarMode(str, Enum):
    """How (or whether) a meter's household has solar generation.

    Inheriting from str as well as Enum means these values serialize to
    plain strings ("NONE", "ON_GRID", "OFF_GRID") in JSON and in the
    database, instead of an opaque enum representation.
    """

    NONE = "NONE"
    ON_GRID = "ON_GRID"
    OFF_GRID = "OFF_GRID"


class BillingFrequency(str, Enum):
    """How often a tariff plan's billing cycle is assessed."""

    BI_MONTHLY = "BI_MONTHLY"
    MONTHLY = "MONTHLY"
