"""Shared pytest fixtures.

Each test gets its own fresh in-memory SQLite database, so tests can't
accidentally affect each other and never touch the real wattledger.db file.
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Import app.models (not just app.models.meter) so every table is registered
# on SQLModel.metadata before create_all() runs.
import app.models  # noqa: F401
from app.models.user import User


@pytest.fixture()
def session():
    # StaticPool keeps the same in-memory database alive across the
    # multiple connections SQLAlchemy may open during a test, instead of
    # each connection getting its own blank in-memory database.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def create_test_user(session, email: str) -> User:
    """A persisted User row, for tests that need *some* owner for a Meter
    without exercising signup themselves (see test_auth_service.py for
    signup/login/forgot-password behavior itself). The security
    question/answer fields are required by the model but irrelevant to
    these tests, so they get placeholder values.
    """
    user = User(
        email=email,
        hashed_password="not-a-real-hash",
        security_question_1="What was the name of your first pet?",
        security_answer_1_hash="not-a-real-hash",
        security_question_2="What city were you born in?",
        security_answer_2_hash="not-a-real-hash",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def user_id(session) -> str:
    return create_test_user(session, "test@example.com").id
