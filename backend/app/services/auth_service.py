"""Signup, login, and forgot-password business logic: validates input,
hashes/checks passwords and security answers, and issues JWT access
tokens. HTTP concerns live in app/api/auth.py.
"""

from sqlmodel import Session

from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.auth import SECURITY_QUESTIONS, normalize_answer
from app.domain.errors import EmailAlreadyRegisteredError, InvalidCredentialsError, NotFoundError
from app.models.user import User
from app.repositories import user_repository

logger = get_logger(__name__)


def _validate_security_question(question: str) -> None:
    if question not in SECURITY_QUESTIONS:
        raise ValueError(f"'{question}' is not one of the offered security questions.")


def signup(
    session: Session,
    *,
    email: str,
    password: str,
    security_question_1: str,
    security_answer_1: str,
    security_question_2: str,
    security_answer_2: str,
) -> tuple[User, str]:
    email = email.strip().lower()
    if user_repository.get_by_email(session, email) is not None:
        raise EmailAlreadyRegisteredError(f"An account already exists for {email}.")

    _validate_security_question(security_question_1)
    _validate_security_question(security_question_2)

    user = User(
        email=email,
        hashed_password=hash_password(password),
        security_question_1=security_question_1,
        security_answer_1_hash=hash_password(normalize_answer(security_answer_1)),
        security_question_2=security_question_2,
        security_answer_2_hash=hash_password(normalize_answer(security_answer_2)),
    )
    created = user_repository.create(session, user)
    logger.info("Created user %s (%s)", created.id, created.email)

    token = create_access_token(created.id)
    return created, token


def login(session: Session, *, email: str, password: str) -> tuple[User, str]:
    email = email.strip().lower()
    user = user_repository.get_by_email(session, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Incorrect email or password.")

    logger.info("User %s logged in", user.id)
    token = create_access_token(user.id)
    return user, token


def get_security_questions(session: Session, *, email: str) -> tuple[str, str]:
    email = email.strip().lower()
    user = user_repository.get_by_email(session, email)
    if user is None:
        raise NotFoundError(f"No account found for {email}.")
    return user.security_question_1, user.security_question_2


def reset_password(
    session: Session,
    *,
    email: str,
    security_answer_1: str,
    security_answer_2: str,
    new_password: str,
) -> tuple[User, str]:
    email = email.strip().lower()
    user = user_repository.get_by_email(session, email)
    if user is None:
        raise NotFoundError(f"No account found for {email}.")

    answers_match = verify_password(
        normalize_answer(security_answer_1), user.security_answer_1_hash
    ) and verify_password(normalize_answer(security_answer_2), user.security_answer_2_hash)
    if not answers_match:
        raise InvalidCredentialsError("Those answers don't match our records.")

    user.hashed_password = hash_password(new_password)
    updated = user_repository.save(session, user)
    logger.info("User %s reset their password via security questions", user.id)

    token = create_access_token(updated.id)
    return updated, token
