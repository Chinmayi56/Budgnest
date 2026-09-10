"""
utils/deps.py

Reusable FastAPI dependencies for authentication and authorization.

- get_current_user: resolves and validates the JWT on every protected
  request, re-checking the user's live status in the database. This is
  the dependency that all financial-data routes should use, and they
  must always scope their MongoDB queries to current_user.id — never
  to a user_id supplied by the client — so each user can only ever
  reach their own data.
- require_roles: a generic role-gate factory kept for possible future
  extensibility. BudgetNest is a single-role (USER) personal
  application today, so no role-based/company-style authorization
  (owner/accountant/employee tiers) is wired up.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.core import AgnosticDatabase

from database import get_database
from models.user import UserRole, UserStatus
from schemas.user import UserPublic
from services.user_service import get_user_by_id, to_public_dict
from utils.jwt_handler import TokenExpiredError, TokenInvalidError, decode_access_token

# auto_error=False so we can raise our own 401 (instead of FastAPI's
# default 403) when the Authorization header is missing entirely.
_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AgnosticDatabase = Depends(get_database),
) -> UserPublic:
    """
    Resolve the currently authenticated user from the 'Authorization:
    Bearer <token>' header. Raises 401 for any missing/malformed/
    invalid/expired token, or an unresolvable/deactivated account.
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Missing or malformed Authorization header")

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except TokenExpiredError:
        raise _unauthorized("Access token has expired")
    except TokenInvalidError:
        raise _unauthorized("Invalid access token")

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Invalid access token payload")

    user_doc = await get_user_by_id(db, user_id)
    if user_doc is None:
        raise _unauthorized("User no longer exists")

    if user_doc["status"] != UserStatus.ACTIVE.value:
        # Distinct from a plain 401: the token itself is valid, but the
        # account is not currently allowed to act.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user_doc['status'].lower()}",
        )

    return UserPublic(**to_public_dict(user_doc))


def require_roles(*allowed_roles: UserRole):
    """
    Factory for a role-gated dependency. Returns 403 if the current
    user's role is not one of `allowed_roles`.

    Not currently used anywhere in BudgetNest — there is only one
    application role (UserRole.USER), so there is nothing to gate on
    today. Kept as a small, generic building block in case a future
    role is ever added; per-user data isolation (below) does not
    depend on this and should never be implemented via roles.

    Usage (hypothetical future role):
        @router.get("/some-route")
        async def handler(user: UserPublic = Depends(require_roles(UserRole.SOME_FUTURE_ROLE))):
            ...
    """

    async def role_checker(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker
