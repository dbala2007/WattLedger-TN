"""Orchestrates tariff plan configuration: creating a plan together with its
subsidy rules and slabs, and looking up the plan/rules/slabs bundle that is
effective for a given date (used by the bill estimate service).
"""

from datetime import date

from sqlmodel import Session

from app.core.logging import get_logger
from app.domain.errors import NotFoundError
from app.domain.tariffs import select_effective_tariff_plan
from app.models.tariff import SubsidyRule, TariffPlan, TariffSlab
from app.repositories import tariff_repository
from app.schemas.tariff import SubsidyRuleCreate, TariffSlabCreate

logger = get_logger(__name__)


def create_tariff_plan(
    session: Session,
    *,
    name: str,
    provider: str,
    consumer_category: str,
    effective_from: date,
    effective_to: date | None,
    billing_frequency,
    fixed_charge,
    source_reference: str,
    active: bool,
    subsidy_rules: list[SubsidyRuleCreate],
    slabs: list[TariffSlabCreate],
) -> tuple[TariffPlan, list[SubsidyRule], list[TariffSlab]]:
    """Creates a tariff plan and its rules/slabs in one call.

    CLAUDE.md section 5 requires tariff versions to be added, never silently
    overwritten - this always inserts a new TariffPlan row rather than
    editing an existing one.
    """
    plan = TariffPlan(
        name=name,
        provider=provider,
        consumer_category=consumer_category,
        effective_from=effective_from,
        effective_to=effective_to,
        billing_frequency=billing_frequency,
        fixed_charge=fixed_charge,
        source_reference=source_reference,
        active=active,
    )
    plan = tariff_repository.create_plan(session, plan)

    saved_rules = [
        tariff_repository.add_subsidy_rule(
            session,
            SubsidyRule(tariff_plan_id=plan.id, **rule.model_dump()),
        )
        for rule in subsidy_rules
    ]
    saved_slabs = [
        tariff_repository.add_slab(
            session,
            TariffSlab(tariff_plan_id=plan.id, **slab.model_dump()),
        )
        for slab in slabs
    ]

    logger.info(
        "Created tariff plan %s (%s), effective %s, source=%s",
        plan.id, plan.name, plan.effective_from, plan.source_reference,
    )
    return plan, saved_rules, saved_slabs


def update_tariff_plan(
    session: Session,
    tariff_plan_id: str,
    *,
    name: str,
    provider: str,
    consumer_category: str,
    effective_from: date,
    effective_to: date | None,
    billing_frequency,
    fixed_charge,
    source_reference: str,
    active: bool,
    subsidy_rules: list[SubsidyRuleCreate],
    slabs: list[TariffSlabCreate],
) -> tuple[TariffPlan, list[SubsidyRule], list[TariffSlab]]:
    """Replaces an existing tariff plan's fields, subsidy rules, and slabs.

    Unlike create_tariff_plan (which always inserts a new version),
    this edits the plan in place - the user asked for full edit support to
    fix data-entry mistakes. Because no BillingAssessment records reference
    tariff plans yet, this is safe today; once historical bills exist,
    editing a plan they relied on would need to be reconsidered (see
    PRP.md section 5's tariff-source policy).
    """
    plan = tariff_repository.get_plan(session, tariff_plan_id)
    if plan is None:
        raise NotFoundError(f"Tariff plan {tariff_plan_id} not found.")

    plan.name = name
    plan.provider = provider
    plan.consumer_category = consumer_category
    plan.effective_from = effective_from
    plan.effective_to = effective_to
    plan.billing_frequency = billing_frequency
    plan.fixed_charge = fixed_charge
    plan.source_reference = source_reference
    plan.active = active
    plan = tariff_repository.save_plan(session, plan)

    tariff_repository.delete_subsidy_rules(session, tariff_plan_id)
    tariff_repository.delete_slabs(session, tariff_plan_id)

    saved_rules = [
        tariff_repository.add_subsidy_rule(
            session,
            SubsidyRule(tariff_plan_id=plan.id, **rule.model_dump()),
        )
        for rule in subsidy_rules
    ]
    saved_slabs = [
        tariff_repository.add_slab(
            session,
            TariffSlab(tariff_plan_id=plan.id, **slab.model_dump()),
        )
        for slab in slabs
    ]

    logger.info("Updated tariff plan %s (%s)", plan.id, plan.name)
    return plan, saved_rules, saved_slabs


def get_tariff_plan_bundle(session: Session, tariff_plan_id: str) -> tuple[TariffPlan, list[SubsidyRule], list[TariffSlab]]:
    plan = tariff_repository.get_plan(session, tariff_plan_id)
    if plan is None:
        raise NotFoundError(f"Tariff plan {tariff_plan_id} not found.")
    return (
        plan,
        tariff_repository.list_subsidy_rules(session, tariff_plan_id),
        tariff_repository.list_slabs(session, tariff_plan_id),
    )


def list_tariff_plans(session: Session, consumer_category: str | None = None) -> list[TariffPlan]:
    return tariff_repository.list_plans(session, consumer_category=consumer_category)


def get_effective_plan_bundle(
    session: Session, *, consumer_category: str, as_of_date: date
) -> tuple[TariffPlan, list[SubsidyRule], list[TariffSlab]]:
    """The plan (with its rules/slabs) effective on as_of_date - raises
    TariffConfigurationError (via app.domain.tariffs) if none is configured.
    """
    all_plans = tariff_repository.list_plans(session, consumer_category=consumer_category)
    plan = select_effective_tariff_plan(all_plans, consumer_category=consumer_category, as_of_date=as_of_date)
    return (
        plan,
        tariff_repository.list_subsidy_rules(session, plan.id),
        tariff_repository.list_slabs(session, plan.id),
    )
