"""
tests/conftest.py

Test setup shared by all authentication tests.

Uses `mongomock-motor` to provide an in-memory, Motor-API-compatible
MongoDB double — so the test suite exercises the real routes/services
code path without requiring a live MongoDB server. This does not add a
second real database technology to the project; it is a test-only
in-memory stand-in for the same MongoDB/Motor interface already used
everywhere else.

Required environment variables are set here (if not already present)
*before* config.py/main.py are imported, since Settings() raises on
missing required variables.
"""

import os
import sys

# Make sure `backend/` (this file's parent's parent) is importable as
# the project root, matching how the app is normally run
# (`uvicorn main:app` from inside backend/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "budgetnest_test")
os.environ.setdefault("JWT_SECRET", "test-only-secret-do-not-use-in-production")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

import database as database_module
import main as main_module
from services.user_service import ensure_indexes


@pytest_asyncio.fixture
async def mock_db():
    """A fresh in-memory MongoDB database for each test."""
    # tz_aware=True to match the real Motor client in database.py
    # (connect_to_mongo), so tests exercise the same timezone-aware
    # datetime behavior as production instead of mongomock-motor's
    # naive-by-default datetimes.
    mock_client = AsyncMongoMockClient(tz_aware=True)
    db = mock_client["budgetnest_test"]
    await ensure_indexes(db)
    yield db


@pytest_asyncio.fixture
async def client(mock_db):
    """
    Async HTTP client wired to the FastAPI app with `get_database`
    overridden to return the in-memory mock database.

    Note: httpx's ASGITransport does not trigger FastAPI startup/shutdown
    events, so the app's real connect_to_mongo() (which targets
    MONGO_URL) never runs during tests — only the mock database is used.
    """
    main_module.app.dependency_overrides[database_module.get_database] = lambda: mock_db
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    main_module.app.dependency_overrides.clear()


@pytest.fixture
def registered_user_payload():
    """A valid registration payload reused across several tests."""
    return {
        "full_name": "Jane User",
        "email": "jane.user@example.com",
        "password": "StrongPassword123",
    }


@pytest.fixture
def second_user_payload():
    """A second, distinct user — used for data-isolation tests."""
    return {
        "full_name": "John Other",
        "email": "john.other@example.com",
        "password": "AnotherStrongPass1",
    }


@pytest_asyncio.fixture
async def auth_headers(client, registered_user_payload):
    """Register + log in a user, returning ('Authorization' header dict, user_id)."""
    await client.post("/api/auth/register", json=registered_user_payload)
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": registered_user_payload["email"], "password": registered_user_payload["password"]},
    )
    body = login_resp.json()
    token = body["access_token"]
    user_id = body["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest_asyncio.fixture
async def second_auth_headers(client, second_user_payload):
    """A second, independent authenticated user — used for data-isolation tests."""
    await client.post("/api/auth/register", json=second_user_payload)
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": second_user_payload["email"], "password": second_user_payload["password"]},
    )
    body = login_resp.json()
    token = body["access_token"]
    user_id = body["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id
