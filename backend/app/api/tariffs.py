"""HTTP endpoints for tariff plan configuration (admin/settings screen)."""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.tariff import SubsidyRuleRead, TariffPlanCreate, TariffPlanRead, TariffSlabRead
from app.services import tariff_service

# Tariff plans are shared TN government tariff schedules, not per-user data
# (unlike meters/readings), so every endpoint just requires *some* logged-in
# user rather than filtering by user_id - hence a router-level dependency
# instead of a current_user parameter on each function.
router = APIRouter(prefix="/tariffs", tags=["tariffs"], dependencies=[Depends(get_current_user)])


def _to_read(plan, rules, slabs) -> TariffPlanRead:
    return TariffPlanRead(
        **plan.model_dump(),
        subsidy_rules=[SubsidyRuleRead.model_validate(r) for r in rules],
        slabs=[TariffSlabRead.model_validate(s) for s in slabs],
    )


@router.post("", response_model=TariffPlanRead, status_code=status.HTTP_201_CREATED)
def create_tariff_plan(payload: TariffPlanCreate, session: Session = Depends(get_session)) -> TariffPlanRead:
    plan, rules, slabs = tariff_service.create_tariff_plan(
        session,
        name=payload.name,
        provider=payload.provider,
        consumer_category=payload.consumer_category,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        billing_frequency=payload.billing_frequency,
        fixed_charge=payload.fixed_charge,
        source_reference=payload.source_reference,
        active=payload.active,
        subsidy_rules=payload.subsidy_rules,
        slabs=payload.slabs,
    )
    return _to_read(plan, rules, slabs)


@router.get("", response_model=list[TariffPlanRead])
def list_tariff_plans(
    consumer_category: str | None = None, session: Session = Depends(get_session)
) -> list[TariffPlanRead]:
    plans = tariff_service.list_tariff_plans(session, consumer_category=consumer_category)
    result = []
    for plan in plans:
        _, rules, slabs = tariff_service.get_tariff_plan_bundle(session, plan.id)
        result.append(_to_read(plan, rules, slabs))
    return result


@router.get("/{tariff_plan_id}", response_model=TariffPlanRead)
def get_tariff_plan(tariff_plan_id: str, session: Session = Depends(get_session)) -> TariffPlanRead:
    plan, rules, slabs = tariff_service.get_tariff_plan_bundle(session, tariff_plan_id)
    return _to_read(plan, rules, slabs)


@router.patch("/{tariff_plan_id}", response_model=TariffPlanRead)
def update_tariff_plan(
    tariff_plan_id: str, payload: TariffPlanCreate, session: Session = Depends(get_session)
) -> TariffPlanRead:
    """Replaces the plan's fields, subsidy rules, and slabs.

    Note this isn't a partial patch like PATCH /meters/{id} - every field,
    including the full list of subsidy_rules and slabs, must be sent, the
    same shape as creating a plan. The rules/slabs are wholesale
    replaced rather than merged, since matching them up field-by-field
    wouldn't be meaningfully simpler than just resending the full set.
    """
    plan, rules, slabs = tariff_service.update_tariff_plan(
        session,
        tariff_plan_id,
        name=payload.name,
        provider=payload.provider,
        consumer_category=payload.consumer_category,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        billing_frequency=payload.billing_frequency,
        fixed_charge=payload.fixed_charge,
        source_reference=payload.source_reference,
        active=payload.active,
        subsidy_rules=payload.subsidy_rules,
        slabs=payload.slabs,
    )
    return _to_read(plan, rules, slabs)
