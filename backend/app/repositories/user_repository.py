"""Database access for User rows."""

from sqlmodel import Session, select

from app.models.user import User


def get_by_id(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)


def get_by_email(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def create(session: Session, user: User) -> User:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def save(session: Session, user: User) -> User:
    """Persists changes to a user row already loaded in this session
    (used by password reset, unlike create() which inserts a new row).
    """
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
