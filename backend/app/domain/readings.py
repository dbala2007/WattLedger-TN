"""Pure business rules for meter readings.

Nothing in this file talks to the database or the API. It only works with
plain values and model objects passed in, and returns values or raises
ReadingValidationError. That is what CLAUDE.md means by keeping business
logic "testable without UI" and reusable across desktop/web/mobile clients.
"""

from decimal import Decimal

from app.models.enums import SolarMode
from app.models.reading import MeterReading


class ReadingValidationError(Exception):
    """Raised when one or more reading validation rules fail.

    Carries a list of human-readable messages so the API/UI can show every
    problem at once instead of one-at-a-time.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def calculate_balance(current: Decimal, previous: Decimal | None) -> Decimal | None:
    """The daily balance is current minus the previous chronological reading.

    A meter's very first reading has no prior value to compare against, so
    its balance is None (not zero) - there is no "usage" to report yet.
    """
    if previous is None:
        return None
    return current - previous


def validate_reading(
    *,
    solar_mode: SolarMode,
    eb_units: Decimal,
    solar_units: Decimal | None,
    previous_eb_units: Decimal | None,
    previous_solar_units: Decimal | None,
    date_already_has_reading: bool,
) -> list[str]:
    """Check the incoming reading against CLAUDE.md's validation rules.

    Returns a list of error messages - empty if the reading is valid. Doing
    validation as "return errors" rather than "raise on first problem" lets
    the caller decide whether to raise, and lets tests assert on the exact
    messages without needing try/except everywhere.
    """
    errors: list[str] = []

    if date_already_has_reading:
        errors.append("A reading already exists for this meter on this date.")

    if solar_mode != SolarMode.NONE and solar_units is None:
        errors.append("Solar Unit is required because this meter has solar tracking enabled.")

    if previous_eb_units is not None and eb_units < previous_eb_units:
        errors.append(
            f"EB Units ({eb_units}) is lower than the previous reading "
            f"({previous_eb_units}). If the meter was replaced or reset, use "
            "the meter reset workflow instead of a normal reading."
        )

    if (
        solar_units is not None
        and previous_solar_units is not None
        and solar_units < previous_solar_units
    ):
        errors.append(
            f"Solar Unit ({solar_units}) is lower than the previous reading "
            f"({previous_solar_units}). If the inverter/meter was replaced or "
            "reset, use the meter reset workflow instead of a normal reading."
        )

    return errors


def recalculate_chain(readings: list[MeterReading]) -> None:
    """Recompute eb_balance/solar_balance for a chronologically-sorted list.

    `readings` must already be sorted ascending by reading_date - this
    function does not sort, so that callers control (and can test) ordering
    explicitly. Each reading's balance is derived from the reading right
    before it in the list, never from database insertion order. This is why
    editing, deleting, or backdating a reading requires re-running this over
    every reading from that point forward (CLAUDE.md section 4).

    Mutates the objects in place; the caller is responsible for saving them.
    """
    previous: MeterReading | None = None
    for reading in readings:
        reading.eb_balance = calculate_balance(reading.eb_units, previous.eb_units if previous else None)

        if reading.solar_units is not None and previous is not None and previous.solar_units is not None:
            reading.solar_balance = calculate_balance(reading.solar_units, previous.solar_units)
        else:
            reading.solar_balance = None

        previous = reading


def sum_balances(readings: list[MeterReading], field: str) -> Decimal:
    """Total of eb_balance or solar_balance across a list of readings.

    A reading with no balance yet (its meter's very first-ever reading, so
    there is no predecessor to compare against) contributes 0 rather than
    being an error - there is simply no usage data from before tracking
    began. Because each reading's balance is already "this reading minus its
    true chronological predecessor" (see recalculate_chain above), summing
    balances over a date range telescopes to closing minus opening reading
    for that range - which is exactly a billing cycle's consumed units.
    """
    total = Decimal("0")
    for reading in readings:
        value = getattr(reading, field)
        if value is not None:
            total += value
    return total
