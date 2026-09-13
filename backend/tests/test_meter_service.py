from datetime import date

import pytest

from app.domain.errors import NotFoundError
from app.models.enums import SolarMode
from app.services import meter_service


def test_create_meter_defaults_cycle_length_to_two_months(session, user_id):
    meter = meter_service.create_meter(session, user_id=user_id, meter_number="EB-1")
    assert meter.cycle_length_months == 2
    assert meter.active is True


def test_create_meter_requires_meter_number(session, user_id):
    with pytest.raises(ValueError):
        meter_service.create_meter(session, user_id=user_id, meter_number="   ")


def test_update_meter_changes_only_provided_fields(session, user_id):
    meter = meter_service.create_meter(session, user_id=user_id, meter_number="EB-1", display_name="Home")
    updated = meter_service.update_meter(session, meter.id, user_id, solar_mode=SolarMode.ON_GRID)

    assert updated.solar_mode == SolarMode.ON_GRID
    assert updated.display_name == "Home"  # unchanged


def test_update_meter_can_deactivate(session, user_id):
    meter = meter_service.create_meter(session, user_id=user_id, meter_number="EB-1")
    updated = meter_service.update_meter(session, meter.id, user_id, active=False)
    assert updated.active is False


def test_update_meter_can_set_billing_cycle_and_assessment_dates(session, user_id):
    meter = meter_service.create_meter(session, user_id=user_id, meter_number="EB-1")
    updated = meter_service.update_meter(
        session,
        meter.id,
        user_id,
        billing_cycle_reference_date=date(2026, 5, 10),
        cycle_length_months=2,
        last_assessment_date=date(2026, 7, 9),
        next_expected_assessment_date=date(2026, 9, 9),
    )
    assert updated.billing_cycle_reference_date == date(2026, 5, 10)
    assert updated.last_assessment_date == date(2026, 7, 9)
    assert updated.next_expected_assessment_date == date(2026, 9, 9)


def test_update_meter_rejects_next_assessment_on_or_before_last(session, user_id):
    meter = meter_service.create_meter(session, user_id=user_id, meter_number="EB-1")
    with pytest.raises(ValueError):
        meter_service.update_meter(
            session,
            meter.id,
            user_id,
            last_assessment_date=date(2026, 7, 9),
            next_expected_assessment_date=date(2026, 7, 9),
        )


def test_update_unknown_meter_raises_not_found(session, user_id):
    with pytest.raises(NotFoundError):
        meter_service.update_meter(session, "does-not-exist", user_id, active=False)


def test_meter_owned_by_another_user_is_not_found(session, user_id):
    from tests.conftest import create_test_user

    other = create_test_user(session, "other@example.com")

    meter = meter_service.create_meter(session, user_id=user_id, meter_number="EB-1")

    with pytest.raises(NotFoundError):
        meter_service.get_meter(session, meter.id, other.id)
