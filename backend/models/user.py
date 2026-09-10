"""
models/user.py

Domain-level definitions for the "users" collection.

MongoDB is schemaless, so this module does not define an ORM model —
it defines the shared vocabulary (roles, statuses) and a small helper
to convert a raw MongoDB document into a plain dict with a string id,
which schemas/services/routes all build on top of.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    """
    Application role.

    BudgetNest is a personal budget and expense management application,
    so there is a single normal application role. The field is kept
    (rather than removed outright) so future extensibility doesn't
    require a schema/DB migration, but no company-style roles
    (owner/accountant/employee) or multi-role authorization are used.
    """

    USER = "USER"


class UserStatus(str, Enum):
    """Account status. Only ACTIVE accounts may log in."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


USERS_COLLECTION = "users"


def new_user_document(full_name: str, email: str, password_hash: str, role: UserRole = UserRole.USER) -> dict[str, Any]:
    """Build the raw MongoDB document for a newly registered user."""
    now = datetime.now(timezone.utc)
    return {
        "full_name": full_name,
        "email": email,
        "password_hash": password_hash,
        "role": role.value,
        "status": UserStatus.ACTIVE.value,
        "created_at": now,
        "updated_at": now,
    }


def user_doc_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a raw MongoDB user document into a plain dict with a
    string 'id' field (instead of Mongo's ObjectId '_id'). Used as the
    common shape that schemas.user.UserPublic is built from.
    """
    return {
        "id": str(doc["_id"]),
        "full_name": doc["full_name"],
        "email": doc["email"],
        "role": doc["role"],
        "status": doc["status"],
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }
