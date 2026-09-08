import pytest

from app.core.security import decode_access_token
from app.domain.auth import SECURITY_QUESTIONS
from app.domain.errors import EmailAlreadyRegisteredError, InvalidCredentialsError, NotFoundError
from app.services import auth_service

Q1, Q2 = SECURITY_QUESTIONS[0], SECURITY_QUESTIONS[1]


def _signup(session, email="alice@example.com", password="correct-horse-battery", answer_1="Rex", answer_2="Chennai"):
    return auth_service.signup(
        session,
        email=email,
        password=password,
        security_question_1=Q1,
        security_answer_1=answer_1,
        security_question_2=Q2,
        security_answer_2=answer_2,
    )


def test_signup_creates_user_and_returns_a_usable_token(session):
    user, token = _signup(session, email="Alice@Example.com")
    assert user.email == "alice@example.com"  # stored lowercase
    assert decode_access_token(token) == user.id


def test_signup_rejects_duplicate_email(session):
    _signup(session, email="alice@example.com")
    with pytest.raises(EmailAlreadyRegisteredError):
        _signup(session, email="ALICE@example.com")


def test_signup_rejects_a_question_not_in_the_offered_list(session):
    with pytest.raises(ValueError):
        auth_service.signup(
            session,
            email="alice@example.com",
            password="correct-horse-battery",
            security_question_1="What is your favorite color?",  # not in SECURITY_QUESTIONS
            security_answer_1="blue",
            security_question_2=Q2,
            security_answer_2="Chennai",
        )


def test_login_with_correct_password_succeeds(session):
    created, _ = _signup(session, email="bob@example.com")
    user, token = auth_service.login(session, email="bob@example.com", password="correct-horse-battery")
    assert user.id == created.id
    assert decode_access_token(token) == created.id


def test_login_with_wrong_password_is_rejected(session):
    _signup(session, email="carol@example.com")
    with pytest.raises(InvalidCredentialsError):
        auth_service.login(session, email="carol@example.com", password="wrong-password")


def test_login_with_unknown_email_is_rejected(session):
    with pytest.raises(InvalidCredentialsError):
        auth_service.login(session, email="nobody@example.com", password="whatever")


def test_decode_access_token_rejects_garbage():
    assert decode_access_token("not-a-real-token") is None


def test_get_security_questions_returns_the_signed_up_questions(session):
    _signup(session, email="dave@example.com")
    q1, q2 = auth_service.get_security_questions(session, email="DAVE@example.com")
    assert (q1, q2) == (Q1, Q2)


def test_get_security_questions_for_unknown_email_raises_not_found(session):
    with pytest.raises(NotFoundError):
        auth_service.get_security_questions(session, email="nobody@example.com")


def test_reset_password_with_correct_answers_succeeds(session):
    created, _ = _signup(session, email="erin@example.com", answer_1="Rex", answer_2="Chennai")

    # Answers are case/whitespace-insensitive.
    user, token = auth_service.reset_password(
        session,
        email="erin@example.com",
        security_answer_1="  REX ",
        security_answer_2="chennai",
        new_password="brand-new-password",
    )
    assert user.id == created.id
    assert decode_access_token(token) == created.id

    # The new password actually works, and the old one no longer does.
    auth_service.login(session, email="erin@example.com", password="brand-new-password")
    with pytest.raises(InvalidCredentialsError):
        auth_service.login(session, email="erin@example.com", password="correct-horse-battery")


def test_reset_password_with_wrong_answer_is_rejected(session):
    _signup(session, email="frank@example.com", answer_1="Rex", answer_2="Chennai")
    with pytest.raises(InvalidCredentialsError):
        auth_service.reset_password(
            session,
            email="frank@example.com",
            security_answer_1="Rex",
            security_answer_2="wrong-city",
            new_password="brand-new-password",
        )


def test_reset_password_for_unknown_email_raises_not_found(session):
    with pytest.raises(NotFoundError):
        auth_service.reset_password(
            session,
            email="nobody@example.com",
            security_answer_1="whatever",
            security_answer_2="whatever",
            new_password="brand-new-password",
        )
