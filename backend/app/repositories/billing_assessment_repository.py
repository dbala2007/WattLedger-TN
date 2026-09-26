"""Database access for BillingAssessment rows."""

from datetime import date

from sqlmodel import Session, select

from app.models.billing_assessment import BillingAssessment


def get(session: Session, assessment_id: str) -> BillingAssessment | None:
    return session.get(BillingAssessment, assessment_id)


def get_by_meter_and_date(session: Session, meter_id: str, assessed_on: date) -> BillingAssessment | None:
    statement = select(BillingAssessment).where(
        BillingAssessment.meter_id == meter_id,
        BillingAssessment.assessed_on == assessed_on,
    )
    return session.exec(statement).first()


def list_for_meter(session: Session, meter_id: str) -> list[BillingAssessment]:
    """All assessments for a meter, oldest first - the order cycles are built in."""
    statement = (
        select(BillingAssessment)
        .where(BillingAssessment.meter_id == meter_id)
        .order_by(BillingAssessment.assessed_on.asc())
    )
    return list(session.exec(statement))


def save(session: Session, assessment: BillingAssessment) -> BillingAssessment:
    """Insert or update - SQLModel's session.add handles both."""
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def delete(session: Session, assessment: BillingAssessment) -> None:
    session.delete(assessment)
    session.commit()
