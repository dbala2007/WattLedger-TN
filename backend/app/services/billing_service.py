"""Orchestrates the current billing cycle and bill estimate for a meter:
works out the cycle window, sums this cycle's readings, picks the
effective tariff plan, and runs the tariff engine over the total.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.core.logging import get_logger
from app.core.timezone import today_local
from app.domain.billing_cycles import get_current_cycle_for_meter
from app.domain.readings import sum_balances
from app.domain.tariffs import BillBreakdown, calculate_bill
from app.repositories import reading_repository
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

    readings_in_cycle = reading_repository.list_for_meter(session, meter_id, start_date=period_start, end_date=period_end)
    total_eb_units = sum_balances(readings_in_cycle, "eb_balance")
    total_solar_units = sum_balances(readings_in_cycle, "solar_balance")

    if not readings_in_cycle:
        return CurrentBillEstimate(
            meter_id=meter_id,
            period_start=period_start,
            period_end=period_end,
            total_eb_units=Decimal("0"),
            total_solar_units=Decimal("0"),
            reading_count=0,
            breakdown=None,
            note="No readings recorded yet for this billing cycle.",
        )

    plan, subsidy_rules, slabs = tariff_service.get_effective_plan_bundle(
        session, consumer_category="DOMESTIC", as_of_date=as_of_date
    )
    breakdown = calculate_bill(
        total_units=total_eb_units,
        tariff_plan=plan,
        subsidy_rules=subsidy_rules,
        slabs=slabs,
        as_of_date=as_of_date,
    )

    logger.info(
        "Estimated bill for meter %s, cycle %s..%s: %s units -> Rs.%s",
        meter_id, period_start, period_end, total_eb_units, breakdown.total_estimated_amount,
    )

    return CurrentBillEstimate(
        meter_id=meter_id,
        period_start=period_start,
        period_end=period_end,
        total_eb_units=total_eb_units,
        total_solar_units=total_solar_units,
        reading_count=len(readings_in_cycle),
        breakdown=breakdown,
    )
