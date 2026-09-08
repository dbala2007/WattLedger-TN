"""Database engine and session management.

SQLModel sits on top of SQLAlchemy, so an "engine" here is the object that
knows how to talk to the SQLite file, and a "session" is a single unit-of-work
(a transaction) used to read/write rows.

Swapping SQLite for PostgreSQL later (per PRP NFR-003) should only require
changing DATABASE_URL - nothing in the models/domain/service layers should
need to change.
"""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# check_same_thread=False is needed because SQLite normally only allows the
# thread that created a connection to use it, but FastAPI can serve requests
# from different threads. This is the standard SQLite + FastAPI setting.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args)


def create_db_and_tables() -> None:
    """Create any tables that don't exist yet, based on imported SQLModel models."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and closes it afterwards."""
    with Session(engine) as session:
        yield session
