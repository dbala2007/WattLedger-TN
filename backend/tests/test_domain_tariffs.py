"""Boundary tests for the tariff calculation engine (app.domain.tariffs).

CLAUDE.md section 15: "Never consider the tariff engine complete without
boundary tests." The example tariff plan here mirrors PRP.md section 4's
rule_groups example (200 free units up to 500 units/cycle, 100 free units
above), with clearly made-up example rates - not real TNPDCL numbers.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import TariffConfigurationError
from app.domain.tariffs import calculate_bill, select_effective_tariff_plan, select_subsidy_rule
from app.models.tariff import SubsidyRule, TariffPlan, TariffSlab

PLAN_DATE = date(2026, 5, 10)


def _example_plan(fixed_charge: str = "50") -> TariffPlan:
    return TariffPlan(
        id="tp1",
        name="TN Domestic Example",
        effective_from=PLAN_DATE,
        source_reference="EXAMPLE/PLACEHOLDER - not a verified TNERC order",
        fixed_charge=Decimal(fixed_charge),
    )


def _example_subsidy_rules() -> list[SubsidyRule]:
    return [
        SubsidyRule(
            tariff_plan_id="tp1",
            rule_name="cycle_upto_500",
            consumption_min=Decimal("0"),
            consumption_max=Decimal("500"),
            free_units=Decimal("200"),
            effective_from=PLAN_DATE,
        ),
        SubsidyRule(
            tariff_plan_id="tp1",
            rule_name="cycle_above_500",
            consumption_min=Decimal("500.0001"),
            consumption_max=None,
            free_units=Decimal("100"),
            effective_from=PLAN_DATE,
        ),
    ]


def _example_slabs() -> list[TariffSlab]:
    return [
        TariffSlab(tariff_plan_id="tp1", rule_group="cycle_upto_500", from_unit=Decimal("0"), to_unit=Decimal("100"), rate_per_unit=Decimal("3.00"), sort_order=1),
        TariffSlab(tariff_plan_id="tp1", rule_group="cycle_upto_500", from_unit=Decimal("100"), to_unit=Decimal("200"), rate_per_unit=Decimal("4.00"), sort_order=2),
        TariffSlab(tariff_plan_id="tp1", rule_group="cycle_upto_500", from_unit=Decimal("200"), to_unit=None, rate_per_unit=Decimal("5.00"), sort_order=3),
        TariffSlab(tariff_plan_id="tp1", rule_group="cycle_above_500", from_unit=Decimal("0"), to_unit=Decimal("100"), rate_per_unit=Decimal("4.00"), sort_order=1),
        TariffSlab(tariff_plan_id="tp1", rule_group="cycle_above_500", from_unit=Decimal("100"), to_unit=Decimal("200"), rate_per_unit=Decimal("5.00"), sort_order=2),
        TariffSlab(tariff_plan_id="tp1", rule_group="cycle_above_500", from_unit=Decimal("200"), to_unit=Decimal("500"), rate_per_unit=Decimal("6.50"), sort_order=3),
        TariffSlab(tariff_plan_id="tp1", rule_group="cycle_above_500", from_unit=Decimal("500"), to_unit=None, rate_per_unit=Decimal("8.00"), sort_order=4),
    ]


def _bill(total_units: str):
    return calculate_bill(
        total_units=Decimal(total_units),
        tariff_plan=_example_plan(),
        subsidy_rules=_example_subsidy_rules(),
        slabs=_example_slabs(),
        as_of_date=PLAN_DATE,
    )


def test_exactly_at_subsidy_threshold_uses_upto_group():
    breakdown = _bill("500")
    assert breakdown.rule_group == "cycle_upto_500"
    assert breakdown.free_units_applied == Decimal("200")
    assert breakdown.chargeable_units == Decimal("300")
    assert [sc.units_charged for sc in breakdown.slab_charges] == [Decimal("100"), Decimal("100"), Decimal("100")]
    assert breakdown.total_estimated_amount == Decimal("1250.00")  # 300+400+500 + 50 fixed


def test_one_unit_above_subsidy_threshold_uses_above_group():
    breakdown = _bill("501")
    assert breakdown.rule_group == "cycle_above_500"
    assert breakdown.free_units_applied == Decimal("100")
    assert breakdown.chargeable_units == Decimal("401")
    # slab1: 100@4=400, slab2: 100@5=500, slab3: 201@6.5=1306.5
    assert breakdown.total_estimated_amount == Decimal("2256.5000")


def test_first_slab_upper_boundary():
    # total=300 -> free 200 -> chargeable exactly 100, filling only slab 1.
    breakdown = _bill("300")
    assert len(breakdown.slab_charges) == 1
    assert breakdown.slab_charges[0].units_charged == Decimal("100")
    assert breakdown.total_estimated_amount == Decimal("350.00")  # 100*3 + 50


def test_second_slab_upper_boundary():
    # total=400 -> chargeable exactly 200, filling slabs 1 and 2.
    breakdown = _bill("400")
    assert len(breakdown.slab_charges) == 2
    assert breakdown.total_estimated_amount == Decimal("750.00")  # 100*3 + 100*4 + 50


def test_above_group_top_slab_boundary_exactly_full():
    # total=600 -> free 100 -> chargeable exactly 500, ending precisely at
    # the boundary of the 200-500 slab; the unlimited 500+ slab should not
    # be charged at all.
    breakdown = _bill("600")
    assert len(breakdown.slab_charges) == 3
    assert breakdown.total_estimated_amount == Decimal("2900.0000")  # 400+500+1950 + 50


def test_above_group_unlimited_top_slab_engages_one_unit_past_boundary():
    # total=600.0001 -> chargeable 500.0001, one ten-thousandth past the
    # 200-500 slab, so the unlimited top slab must engage for that sliver.
    breakdown = _bill("600.0001")
    assert len(breakdown.slab_charges) == 4
    assert breakdown.slab_charges[-1].units_charged == Decimal("0.0001")
    assert breakdown.slab_charges[-1].amount == Decimal("0.0008")


def test_chargeable_units_never_negative_when_below_free_allowance():
    breakdown = _bill("50")  # well under the 200 free units
    assert breakdown.chargeable_units == Decimal("0")
    assert breakdown.slab_charges == []
    assert breakdown.total_estimated_amount == Decimal("50")  # just the fixed charge


def test_negative_total_units_is_rejected():
    with pytest.raises(ValueError):
        calculate_bill(
            total_units=Decimal("-1"),
            tariff_plan=_example_plan(),
            subsidy_rules=_example_subsidy_rules(),
            slabs=_example_slabs(),
            as_of_date=PLAN_DATE,
        )


def test_missing_subsidy_rule_coverage_raises_configuration_error():
    incomplete_rules = [_example_subsidy_rules()[0]]  # only covers 0-500
    with pytest.raises(TariffConfigurationError):
        select_subsidy_rule(Decimal("1000"), incomplete_rules, PLAN_DATE)


def test_overlapping_subsidy_rules_raise_configuration_error():
    rules = _example_subsidy_rules()
    rules.append(
        SubsidyRule(
            tariff_plan_id="tp1",
            rule_name="overlap",
            consumption_min=Decimal("400"),
            consumption_max=Decimal("600"),
            free_units=Decimal("150"),
            effective_from=PLAN_DATE,
        )
    )
    with pytest.raises(TariffConfigurationError):
        select_subsidy_rule(Decimal("450"), rules, PLAN_DATE)


def test_slabs_not_covering_full_chargeable_range_raises_configuration_error():
    slabs_missing_top = [s for s in _example_slabs() if not (s.rule_group == "cycle_upto_500" and s.to_unit is None)]
    with pytest.raises(TariffConfigurationError):
        calculate_bill(
            total_units=Decimal("500"),
            tariff_plan=_example_plan(),
            subsidy_rules=_example_subsidy_rules(),
            slabs=slabs_missing_top,
            as_of_date=PLAN_DATE,
        )


def test_select_effective_tariff_plan_picks_latest_matching_version():
    old_plan = TariffPlan(
        id="old", name="Old", effective_from=date(2024, 1, 1), effective_to=date(2026, 5, 9),
        source_reference="old order",
    )
    new_plan = TariffPlan(
        id="new", name="New", effective_from=PLAN_DATE, effective_to=None,
        source_reference="new order",
    )
    selected = select_effective_tariff_plan(
        [old_plan, new_plan], consumer_category="DOMESTIC", as_of_date=date(2026, 6, 1)
    )
    assert selected.id == "new"


def test_select_effective_tariff_plan_uses_version_effective_during_historical_period():
    old_plan = TariffPlan(
        id="old", name="Old", effective_from=date(2024, 1, 1), effective_to=date(2026, 5, 9),
        source_reference="old order",
    )
    new_plan = TariffPlan(
        id="new", name="New", effective_from=PLAN_DATE, effective_to=None,
        source_reference="new order",
    )
    # A historical bill from before the new plan took effect must keep
    # using the old plan (PRP.md acceptance criteria section 9).
    selected = select_effective_tariff_plan(
        [old_plan, new_plan], consumer_category="DOMESTIC", as_of_date=date(2025, 3, 1)
    )
    assert selected.id == "old"


def test_select_effective_tariff_plan_raises_when_none_match():
    with pytest.raises(TariffConfigurationError):
        select_effective_tariff_plan([], consumer_category="DOMESTIC", as_of_date=PLAN_DATE)
