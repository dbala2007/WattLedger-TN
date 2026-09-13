"""Pure tariff calculation engine.

Given a total billing-cycle consumption and a tariff plan's subsidy rules +
slabs, work out free units, chargeable units, and a slab-by-slab cost
breakdown. Nothing here touches the database - it only reads the plain
values/model objects passed in - so every rule (including every slab
boundary) can be pinned down with a fast unit test (CLAUDE.md section 15
requires boundary tests before the tariff engine is considered complete).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.domain.errors import TariffConfigurationError
from app.models.tariff import SubsidyRule, TariffPlan, TariffSlab


@dataclass
class SlabCharge:
    """One row of the "slabs applied" breakdown (PRP.md FR-007)."""

    rule_group: str
    from_unit: Decimal
    to_unit: Decimal | None
    rate_per_unit: Decimal
    units_charged: Decimal
    amount: Decimal


@dataclass
class BillBreakdown:
    """Everything CLAUDE.md section 5 ("Calculation transparency") requires
    to be shown for a bill estimate - never just a final amount.
    """

    total_units: Decimal
    rule_group: str
    free_units_applied: Decimal
    chargeable_units: Decimal
    solar_units_offset: Decimal = Decimal("0")
    slab_charges: list[SlabCharge] = field(default_factory=list)
    fixed_charge: Decimal = Decimal("0")
    total_estimated_amount: Decimal = Decimal("0")
    tariff_plan_id: str = ""
    tariff_plan_name: str = ""
    tariff_effective_from: date | None = None
    tariff_source_reference: str = ""


def select_subsidy_rule(
    total_units: Decimal,
    subsidy_rules: list[SubsidyRule],
    as_of_date: date,
) -> SubsidyRule:
    """Pick the one subsidy rule whose consumption band contains total_units
    and whose effective-date range covers as_of_date.

    Raises TariffConfigurationError if zero or more than one rule matches -
    both indicate the tariff plan's SubsidyRule rows are misconfigured
    (a gap or an overlap in the consumption bands).
    """
    matches = [
        rule
        for rule in subsidy_rules
        if rule.consumption_min <= total_units
        and (rule.consumption_max is None or total_units <= rule.consumption_max)
        and rule.effective_from <= as_of_date
        and (rule.effective_to is None or rule.effective_to >= as_of_date)
    ]

    if not matches:
        raise TariffConfigurationError(
            f"No subsidy rule covers {total_units} units as of {as_of_date}. "
            "Check the tariff plan's subsidy rule consumption bands."
        )
    if len(matches) > 1:
        names = ", ".join(m.rule_name for m in matches)
        raise TariffConfigurationError(
            f"Multiple subsidy rules ({names}) match {total_units} units as of "
            f"{as_of_date}. Consumption bands must not overlap."
        )
    return matches[0]


def calculate_bill(
    *,
    total_units: Decimal,
    tariff_plan: TariffPlan,
    subsidy_rules: list[SubsidyRule],
    slabs: list[TariffSlab],
    as_of_date: date,
    solar_units_generated: Decimal = Decimal("0"),
) -> BillBreakdown:
    """Compute the full bill breakdown for one billing cycle's consumption.

    solar_units_generated is a net-metering credit: it reduces the
    post-subsidy chargeable units directly (never below zero - generating
    more than you have left to pay for doesn't create a negative bill).
    total_units and the subsidy-rule/slab selection are unaffected - the
    free-unit threshold is based on gross consumption drawn from the grid,
    not net of self-generation. Callers are responsible for only passing a
    non-zero value for meters where this actually applies (grid-tied/on-grid
    solar) - this function doesn't know a meter's solar_mode.
    """
    if total_units < 0:
        raise ValueError("total_units cannot be negative.")
    if solar_units_generated < 0:
        raise ValueError("solar_units_generated cannot be negative.")

    rule = select_subsidy_rule(total_units, subsidy_rules, as_of_date)

    free_units = rule.free_units
    chargeable_units = total_units - free_units
    if chargeable_units < 0:
        chargeable_units = Decimal("0")

    solar_units_offset = min(solar_units_generated, chargeable_units)
    chargeable_units -= solar_units_offset

    group_slabs = sorted(
        (s for s in slabs if s.rule_group == rule.rule_name),
        key=lambda s: (s.sort_order, s.from_unit),
    )

    slab_charges: list[SlabCharge] = []
    remaining = chargeable_units
    for slab in group_slabs:
        if remaining <= 0:
            break

        if slab.to_unit is not None:
            slab_width = slab.to_unit - slab.from_unit
            units_in_slab = min(remaining, slab_width)
        else:
            units_in_slab = remaining

        if units_in_slab > 0:
            amount = units_in_slab * slab.rate_per_unit
            slab_charges.append(
                SlabCharge(
                    rule_group=slab.rule_group,
                    from_unit=slab.from_unit,
                    to_unit=slab.to_unit,
                    rate_per_unit=slab.rate_per_unit,
                    units_charged=units_in_slab,
                    amount=amount,
                )
            )
            remaining -= units_in_slab

    if remaining > 0:
        raise TariffConfigurationError(
            f"Slabs for rule group '{rule.rule_name}' do not cover the full "
            f"chargeable range - {remaining} units left unallocated. The last "
            "slab in a rule group must have to_unit left unset (unlimited)."
        )

    slab_total = sum((sc.amount for sc in slab_charges), Decimal("0"))
    total_amount = slab_total + tariff_plan.fixed_charge

    return BillBreakdown(
        total_units=total_units,
        rule_group=rule.rule_name,
        free_units_applied=free_units,
        chargeable_units=chargeable_units,
        solar_units_offset=solar_units_offset,
        slab_charges=slab_charges,
        fixed_charge=tariff_plan.fixed_charge,
        total_estimated_amount=total_amount,
        tariff_plan_id=tariff_plan.id or "",
        tariff_plan_name=tariff_plan.name,
        tariff_effective_from=tariff_plan.effective_from,
        tariff_source_reference=tariff_plan.source_reference,
    )


def select_effective_tariff_plan(
    plans: list[TariffPlan],
    *,
    consumer_category: str,
    as_of_date: date,
) -> TariffPlan:
    """Pick the tariff plan effective for as_of_date (PRP.md acceptance
    criteria section 9: "the estimate must select the version effective for
    the billing period"). If more than one active plan's date range covers
    as_of_date, the one with the latest effective_from wins - it is the most
    recently issued applicable order.
    """
    matches = [
        p
        for p in plans
        if p.active
        and p.consumer_category == consumer_category
        and p.effective_from <= as_of_date
        and (p.effective_to is None or p.effective_to >= as_of_date)
    ]
    if not matches:
        raise TariffConfigurationError(
            f"No active '{consumer_category}' tariff plan is effective on {as_of_date}."
        )
    return max(matches, key=lambda p: p.effective_from)
