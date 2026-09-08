"""Password hashing and JWT access tokens.

Kept as small, framework-free functions so they're easy to unit test and
easy to reason about: hash_password/verify_password never touch the raw
password after hashing, and create_access_token/decode_access_token never
touch the database - they only encode/decode the user id.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

_JWT_ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Returns the user id encoded in the token, or None if the token is
    missing, malformed, expired, or signed with a different secret key.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
