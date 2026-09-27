"""Tests for "Keep me logged in" - remembered devices and refresh tokens."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import select

from app.core.config import settings
from app.core.security import decode_access_token, hash_refresh_token
from app.domain.errors import InvalidCredentialsError
from app.models.device_session import DeviceSession
from app.services import auth_service, device_session_service
from tests.test_auth_service import _signup


def _stored(session, refresh_token) -> DeviceSession:
    return session.exec(
        select(DeviceSession).where(DeviceSession.token_hash == hash_refresh_token(refresh_token))
    ).one()


def test_remembered_device_gets_new_access_token_without_password(session):
    user, _ = _signup(session)
    refresh_token = device_session_service.create_device_session(session, user_id=user.id, device_name="Android")

    access_token = device_session_service.refresh_access_token(session, refresh_token=refresh_token)

    assert decode_access_token(access_token) == user.id


def test_only_a_hash_of_the_refresh_token_is_stored(session):
    user, _ = _signup(session)
    refresh_token = device_session_service.create_device_session(session, user_id=user.id, device_name="Windows")

    row = _stored(session, refresh_token)
    assert row.token_hash != refresh_token
    assert row.device_name == "Windows"


def test_each_device_gets_its_own_token(session):
    user, _ = _signup(session)
    phone = device_session_service.create_device_session(session, user_id=user.id, device_name="Android")
    laptop = device_session_service.create_device_session(session, user_id=user.id, device_name="Windows")
    assert phone != laptop

    # Logging the phone out leaves the laptop logged in.
    device_session_service.revoke_device_session(session, refresh_token=phone)
    with pytest.raises(InvalidCredentialsError):
        device_session_service.refresh_access_token(session, refresh_token=phone)
    device_session_service.refresh_access_token(session, refresh_token=laptop)


def test_unknown_refresh_token_is_rejected(session):
    with pytest.raises(InvalidCredentialsError):
        device_session_service.refresh_access_token(session, refresh_token="not-a-real-token")


def test_session_unused_for_too_long_is_rejected(session):
    user, _ = _signup(session)
    refresh_token = device_session_service.create_device_session(session, user_id=user.id)
    row = _stored(session, refresh_token)
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.add(row)
    session.commit()

    with pytest.raises(InvalidCredentialsError):
        device_session_service.refresh_access_token(session, refresh_token=refresh_token)


def test_each_use_extends_the_session(session):
    user, _ = _signup(session)
    refresh_token = device_session_service.create_device_session(session, user_id=user.id)
    row = _stored(session, refresh_token)
    # Pretend it was nearly expired.
    row.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    session.add(row)
    session.commit()

    device_session_service.refresh_access_token(session, refresh_token=refresh_token)

    session.refresh(row)
    expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    assert expires_at > datetime.now(timezone.utc) + timedelta(days=settings.remember_me_days - 1)


def test_logging_out_twice_is_harmless(session):
    user, _ = _signup(session)
    refresh_token = device_session_service.create_device_session(session, user_id=user.id)
    device_session_service.revoke_device_session(session, refresh_token=refresh_token)
    device_session_service.revoke_device_session(session, refresh_token=refresh_token)
    device_session_service.revoke_device_session(session, refresh_token="never-existed")


def test_password_reset_signs_out_every_remembered_device(session):
    user, _ = _signup(session, email="erin@example.com", answer_1="Rex", answer_2="Chennai")
    phone = device_session_service.create_device_session(session, user_id=user.id, device_name="Android")
    laptop = device_session_service.create_device_session(session, user_id=user.id, device_name="Windows")

    auth_service.reset_password(
        session, email="erin@example.com", security_answer_1="Rex", security_answer_2="Chennai",
        new_password="brand-new-password",
    )

    for token in (phone, laptop):
        with pytest.raises(InvalidCredentialsError):
            device_session_service.refresh_access_token(session, refresh_token=token)


def test_password_reset_does_not_touch_other_users_devices(session):
    erin, _ = _signup(session, email="erin@example.com", answer_1="Rex", answer_2="Chennai")
    frank, _ = _signup(session, email="frank@example.com")
    franks_phone = device_session_service.create_device_session(session, user_id=frank.id)

    auth_service.reset_password(
        session, email="erin@example.com", security_answer_1="Rex", security_answer_2="Chennai",
        new_password="brand-new-password",
    )

    access_token = device_session_service.refresh_access_token(session, refresh_token=franks_phone)
    assert decode_access_token(access_token) == frank.id
    assert erin.id != frank.id
