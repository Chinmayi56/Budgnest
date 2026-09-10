"""
utils/jwt_handler.py

JWT creation and decoding, built on PyJWT and driven entirely by the
JWT_SECRET / JWT_ALGORITHM / JWT_EXPIRE_MINUTES environment variables
from config.py. No secrets are hard-coded here.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from config import settings


class TokenExpiredError(Exception):
    """Raised when a JWT has expired."""


class TokenInvalidError(Exception):
    """Raised when a JWT is malformed, has a bad signature, or is otherwise invalid."""


def create_access_token(user_id: str, role: str) -> str:
    """
    Create a signed JWT access token for the given user.

    'sub' holds the user's id (string) so the token can be resolved
    back to a user on each request. 'role' is included for convenience
    /debugging only — authorization decisions re-check the role stored
    in the database, not the token, so a stale token can't outlive a
    role or status change.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises TokenExpiredError / TokenInvalidError on any problem so
    callers (utils/deps.py) can translate these into clean 401 responses
    without leaking internal details.
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError("Access token is invalid") from exc
