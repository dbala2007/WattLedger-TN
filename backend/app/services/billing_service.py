"""Orchestrates billing-cycle bill estimates for a meter: works out the
cycle window (the current one, or past ones from the recorded assessment
history), sums that window's readings, picks the effective tariff plan,
and runs the tariff engine over the total.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session

from app.core.logging import get_logger
from app.core.timezone import today_local
from app.domain.billing_cycles import completed_cycles_from_assessments, get_current_cycle_for_meter
from app.domain.errors import TariffConfigurationError
from app.domain.readings import sum_balances
from app.domain.tariffs import BillBreakdown, calculate_bill
from app.models.enums import SolarMode
from app.models.meter import Meter
from app.repositories import billing_assessment_repository, reading_repository
from app.services import meter_service, tariff_service

logger = get_logger(__name__)


@dataclass
class BillingCycleWindow:
    meter_id: str
    period_start: date
    period_end: date


@dataclass
class CurrentBillEstimate:
    meter_id: str
    period_start: date
    period_end: date
    total_eb_units: Decimal
    total_solar_units: Decimal
    reading_count: int
    breakdown: BillBreakdown | None
    note: str | None = None


def get_current_billing_cycle(
    session: Session, meter_id: str, user_id: str, as_of_date: date | None = None
) -> BillingCycleWindow:
    meter = meter_service.get_meter(session, meter_id, user_id)
    as_of_date = as_of_date or today_local()
    period_start, period_end = get_current_cycle_for_meter(meter, as_of_date)
    return BillingCycleWindow(meter_id=meter_id, period_start=period_start, period_end=period_end)


def estimate_current_bill(
    session: Session, meter_id: str, user_id: str, as_of_date: date | None = None
) -> CurrentBillEstimate:
    meter = meter_service.get_meter(session, meter_id, user_id)
    as_of_date = as_of_date or today_local()
    period_start, period_end = get_current_cycle_for_meter(meter, as_of_date)
    # The current cycle is still running, so it is priced with the tariff
    # in force today (as_of_date) - unchanged from before history existed.
    return _estimate_for_period(
        session, meter, period_start, period_end, tariff_date=as_of_date,
        empty_note="No readings recorded yet for this billing cycle.",
    )


@dataclass
class PastCycleBill:
    """One completed cycle from the assessment history, with the official
    bill (if entered) alongside the app's own estimate for comparison.
    """
    opening_assessment_id: str
    closing_assessment_id: str
    official_bill_amount: Decimal | None
    estimate: CurrentBillEstimate

    @property
    def difference(self) -> Decimal | None:
        """Official minus estimated: positive means TNPDCL charged more."""
        estimated = self.estimate.breakdown.total_estimated_amount if self.estimate.breakdown else None
        if self.official_bill_amount is None or estimated is None:
            return None
        return self.official_bill_amount - estimated


def get_billing_history(session: Session, meter_id: str, user_id: str) -> list[PastCycleBill]:
    """Every completed cycle between consecutive recorded assessments,
    newest first, each with its full bill breakdown.

    A past cycle is priced with the tariff version effective on its last
    day (CLAUDE.md section 5: historical bills keep using the tariff that
    applied then, not today's). If no tariff covers an old cycle, that
    cycle still appears with a note instead of failing the whole list.
    """
    meter = meter_service.get_meter(session, meter_id, user_id)
    assessments = billing_assessment_repository.list_for_meter(session, meter_id)
    by_date = {a.assessed_on: a for a in assessments}
    cycles = completed_cycles_from_assessments(list(by_date))

    history = []
    for period_start, period_end in reversed(cycles):
        opening = by_date[period_start]
        # The closing visit is the day after the cycle's last day.
        closing = by_date[period_end + timedelta(days=1)]
        try:
            estimate = _estimate_for_period(
                session, meter, period_start, period_end, tariff_date=period_end,
                empty_note="No readings were recorded during this billing cycle.",
            )
        except TariffConfigurationError as exc:
            estimate = _estimate_for_period(
                session, meter, period_start, period_end, tariff_date=None, empty_note=None,
            )
            estimate.note = f"Cannot estimate this cycle: {exc}"
        history.append(
            PastCycleBill(
                opening_assessment_id=opening.id,
                closing_assessment_id=closing.id,
                official_bill_amount=closing.official_bill_amount,
                estimate=estimate,
            )
        )
    return history


def _estimate_for_period(
    session: Session,
    meter: Meter,
    period_start: date,
    period_end: date,
    *,
    tariff_date: date | None,
    empty_note: str | None,
) -> CurrentBillEstimate:
    """Sum the readings in [period_start, period_end] and price them with
    the tariff effective on tariff_date. tariff_date=None means "totals
    only, don't price" (used when no tariff covers the period).
    """
    readings_in_cycle = reading_repository.list_for_meter(session, meter.id, start_date=period_start, end_date=period_end)
    total_eb_units = sum_balances(readings_in_cycle, "eb_balance")
    total_solar_units = sum_balances(readings_in_cycle, "solar_balance")

    result = CurrentBillEstimate(
        meter_id=meter.id,
        period_start=period_start,
        period_end=period_end,
        total_eb_units=total_eb_units,
        total_solar_units=total_solar_units,
        reading_count=len(readings_in_cycle),
        breakdown=None,
    )
    if not readings_in_cycle:
        result.note = empty_note
        return result
    if tariff_date is None:
        return result

    plan, subsidy_rules, slabs = tariff_service.get_effective_plan_bundle(
        session, consumer_category="DOMESTIC", as_of_date=tariff_date
    )
    # Net-metering credit only makes sense for a grid-tied meter: off-grid
    # solar is self-consumed before the EB reading is even taken (already
    # reflected in a lower eb_balance, not a separate credit to apply here).
    solar_units_generated = total_solar_units if meter.solar_mode == SolarMode.ON_GRID else Decimal("0")

    result.breakdown = calculate_bill(
        total_units=total_eb_units,
        tariff_plan=plan,
        subsidy_rules=subsidy_rules,
        slabs=slabs,
        as_of_date=tariff_date,
        solar_units_generated=solar_units_generated,
    )

    logger.info(
        "Estimated bill for meter %s, cycle %s..%s: %s units -> Rs.%s",
        meter.id, period_start, period_end, total_eb_units, result.breakdown.total_estimated_amount,
    )
    return result
