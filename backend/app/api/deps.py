"""Shared FastAPI dependencies for authenticated endpoints."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.security import decode_access_token
from app.db.session import get_session
from app.domain.errors import InvalidCredentialsError
from app.models.user import User
from app.repositories import user_repository

# auto_error=True means FastAPI itself returns 401 if the Authorization
# header is missing entirely, before this function even runs.
_bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Reads the 'Authorization: Bearer <token>' header, verifies the JWT,
    and loads the User it names. Raises InvalidCredentialsError (mapped to
    HTTP 401 in main.py) for a missing, expired, or forged token, or one
    naming a user that no longer exists.
    """
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise InvalidCredentialsError("Invalid or expired login token. Please log in again.")

    user = user_repository.get_by_id(session, user_id)
    if user is None:
        raise InvalidCredentialsError("Invalid or expired login token. Please log in again.")

    return user
