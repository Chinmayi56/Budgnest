"""
services/user_service.py

Business logic / data-access layer for users. Routes call into this
module rather than talking to MongoDB directly, so the database
interaction stays testable and swappable (see tests/conftest.py, which
overrides get_database with an in-memory Mongo mock).
"""

from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.core import AgnosticDatabase

from models.user import (
    USERS_COLLECTION,
    UserRole,
    UserStatus,
    new_user_document,
    user_doc_to_dict,
)
from utils.security import hash_password, verify_password


async def ensure_indexes(db: AgnosticDatabase) -> None:
    """Create required indexes. Safe to call every startup (idempotent)."""
    await db[USERS_COLLECTION].create_index("email", unique=True)


async def get_user_by_email(db: AgnosticDatabase, email: str) -> Optional[dict[str, Any]]:
    """Fetch a raw user document by email (case-insensitive), or None."""
    return await db[USERS_COLLECTION].find_one({"email": email.lower()})


async def get_user_by_id(db: AgnosticDatabase, user_id: str) -> Optional[dict[str, Any]]:
    """Fetch a raw user document by its Mongo _id (string form), or None."""
    try:
        object_id = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    return await db[USERS_COLLECTION].find_one({"_id": object_id})


async def email_exists(db: AgnosticDatabase, email: str) -> bool:
    return await get_user_by_email(db, email) is not None


async def create_user(
    db: AgnosticDatabase,
    full_name: str,
    email: str,
    password: str,
    role: UserRole,
) -> dict[str, Any]:
    """
    Create a new user with a securely hashed password.
    Caller is responsible for checking email_exists() first if a clean
    "duplicate email" error is desired (this also guards against races
    via the unique index created in ensure_indexes()).
    """
    password_hash = hash_password(password)
    document = new_user_document(
        full_name=full_name,
        email=email.lower(),
        password_hash=password_hash,
        role=role,
    )
    result = await db[USERS_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def authenticate_user(db: AgnosticDatabase, email: str, password: str) -> Optional[dict[str, Any]]:
    """
    Verify credentials. Returns the raw user document on success, or
    None on any failure (unknown email or wrong password) — callers
    should respond identically for both cases to avoid revealing which
    emails are registered.

    Does NOT check account status; that's a separate, explicit check
    in routes/auth.py so a distinct error message can be returned for
    inactive/suspended accounts.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def to_public_dict(user_doc: dict[str, Any]) -> dict[str, Any]:
    """Convert a raw DB user document to the safe, public-facing shape."""
    return user_doc_to_dict(user_doc)
