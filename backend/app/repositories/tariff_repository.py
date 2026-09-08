"""Database access for TariffPlan, SubsidyRule, and TariffSlab rows."""

from sqlmodel import Session, select

from app.models.tariff import SubsidyRule, TariffPlan, TariffSlab


def get_plan(session: Session, tariff_plan_id: str) -> TariffPlan | None:
    return session.get(TariffPlan, tariff_plan_id)


def list_plans(session: Session, consumer_category: str | None = None) -> list[TariffPlan]:
    statement = select(TariffPlan)
    if consumer_category is not None:
        statement = statement.where(TariffPlan.consumer_category == consumer_category)
    return list(session.exec(statement))


def create_plan(session: Session, plan: TariffPlan) -> TariffPlan:
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def list_subsidy_rules(session: Session, tariff_plan_id: str) -> list[SubsidyRule]:
    statement = select(SubsidyRule).where(SubsidyRule.tariff_plan_id == tariff_plan_id)
    return list(session.exec(statement))


def add_subsidy_rule(session: Session, rule: SubsidyRule) -> SubsidyRule:
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


def list_slabs(session: Session, tariff_plan_id: str) -> list[TariffSlab]:
    statement = select(TariffSlab).where(TariffSlab.tariff_plan_id == tariff_plan_id)
    return list(session.exec(statement))


def add_slab(session: Session, slab: TariffSlab) -> TariffSlab:
    session.add(slab)
    session.commit()
    session.refresh(slab)
    return slab


def save_plan(session: Session, plan: TariffPlan) -> TariffPlan:
    """Persists changes to a plan already loaded in this session (used by
    update, unlike create_plan which inserts a brand new row)."""
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def delete_subsidy_rules(session: Session, tariff_plan_id: str) -> None:
    for rule in list_subsidy_rules(session, tariff_plan_id):
        session.delete(rule)
    session.commit()


def delete_slabs(session: Session, tariff_plan_id: str) -> None:
    for slab in list_slabs(session, tariff_plan_id):
        session.delete(slab)
    session.commit()
