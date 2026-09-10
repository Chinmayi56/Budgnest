"""
tests/test_auth.py

Automated tests for the Step 2 authentication system:
registration, login, JWT validation, /auth/me, role/status handling,
and password-hashing safety.

Run with (from backend/, virtual environment active):
    pytest -v
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from config import settings
from models.user import UserStatus, new_user_document, UserRole
from utils.security import hash_password


# ---------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------

async def test_register_success(client, registered_user_payload):
    response = await client.post("/api/auth/register", json=registered_user_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == registered_user_payload["email"]
    assert body["full_name"] == registered_user_payload["full_name"]
    assert body["role"] == "USER"
    assert body["status"] == "ACTIVE"
    assert "id" in body
    # Never returned, in any form:
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email_rejected(client, registered_user_payload):
    first = await client.post("/api/auth/register", json=registered_user_payload)
    assert first.status_code == 201

    second = await client.post("/api/auth/register", json=registered_user_payload)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


async def test_register_ignores_client_supplied_role(client, registered_user_payload):
    # role is not part of UserRegisterRequest, so a client-supplied
    # "role" field must be ignored, never trusted, and every
    # self-registered account must end up as UserRole.USER.
    payload = {**registered_user_payload, "email": "wannabe.owner@example.com", "role": "OWNER"}
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    assert response.json()["role"] == "USER"


async def test_register_weak_password_rejected(client, registered_user_payload):
    payload = {**registered_user_payload, "email": "shortpw@example.com", "password": "short"}
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 422


# ---------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------

async def test_login_success(client, registered_user_payload):
    await client.post("/api/auth/register", json=registered_user_payload)

    response = await client.post(
        "/api/auth/login",
        json={"email": registered_user_payload["email"], "password": registered_user_payload["password"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 0
    assert body["user"]["email"] == registered_user_payload["email"]
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


async def test_login_wrong_password(client, registered_user_payload):
    await client.post("/api/auth/register", json=registered_user_payload)

    response = await client.post(
        "/api/auth/login",
        json={"email": registered_user_payload["email"], "password": "TheWrongPassword123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


async def test_login_nonexistent_user(client):
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "DoesNotMatter123"},
    )

    assert response.status_code == 401
    # Must be identical to the wrong-password message, so email
    # existence can't be inferred from the response.
    assert response.json()["detail"] == "Invalid email or password"


async def test_login_inactive_account_rejected(client, mock_db):
    doc = new_user_document(
        full_name="Inactive User",
        email="inactive@example.com",
        password_hash=hash_password("SomePassword123"),
        role=UserRole.USER,
    )
    doc["status"] = UserStatus.INACTIVE.value
    await mock_db["users"].insert_one(doc)

    response = await client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "SomePassword123"},
    )

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


async def test_login_suspended_account_rejected(client, mock_db):
    doc = new_user_document(
        full_name="Suspended User",
        email="suspended@example.com",
        password_hash=hash_password("SomePassword123"),
        role=UserRole.USER,
    )
    doc["status"] = UserStatus.SUSPENDED.value
    await mock_db["users"].insert_one(doc)

    response = await client.post(
        "/api/auth/login",
        json={"email": "suspended@example.com", "password": "SomePassword123"},
    )

    assert response.status_code == 403
    assert "suspended" in response.json()["detail"].lower()


# ---------------------------------------------------------------------
# /auth/me + JWT validation
# ---------------------------------------------------------------------

async def test_me_with_valid_token(client, registered_user_payload):
    await client.post("/api/auth/register", json=registered_user_payload)
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": registered_user_payload["email"], "password": registered_user_payload["password"]},
    )
    token = login_resp.json()["access_token"]

    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == registered_user_payload["email"]
    assert "password_hash" not in body


async def test_me_without_token(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_malformed_header(client):
    response = await client.get("/api/auth/me", headers={"Authorization": "NotBearerAtAll"})
    assert response.status_code in (401, 403)


async def test_me_invalid_token(client):
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )
    assert response.status_code == 401


async def test_me_expired_token(client, registered_user_payload):
    register_resp = await client.post("/api/auth/register", json=registered_user_payload)
    user_id = register_resp.json()["id"]

    # Manually craft an already-expired token using the app's real secret.
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": user_id,
        "role": "USER",
        "iat": now - timedelta(minutes=120),
        "exp": now - timedelta(minutes=60),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


async def test_logout_requires_valid_token(client, registered_user_payload):
    await client.post("/api/auth/register", json=registered_user_payload)
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": registered_user_payload["email"], "password": registered_user_payload["password"]},
    )
    token = login_resp.json()["access_token"]

    response = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


# ---------------------------------------------------------------------
# Password hashing safety
# ---------------------------------------------------------------------

async def test_password_is_hashed_and_never_returned(client, mock_db, registered_user_payload):
    response = await client.post("/api/auth/register", json=registered_user_payload)
    assert response.status_code == 201

    # Response never includes password material in any field name.
    body_text = response.text.lower()
    assert "password" not in body_text

    # The stored document has a bcrypt hash, not the plain password.
    stored = await mock_db["users"].find_one({"email": registered_user_payload["email"]})
    assert stored["password_hash"] != registered_user_payload["password"]
    assert stored["password_hash"].startswith("$2b$") or stored["password_hash"].startswith("$2a$")


# ---------------------------------------------------------------------
# Backward compatibility (Step 1)
# ---------------------------------------------------------------------

async def test_health_endpoint_still_works(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
