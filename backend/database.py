"""
database.py

MongoDB connection management using Motor's AsyncIOMotorClient.

Exposes:
- connect_to_mongo(): create the client + verify connectivity (call on startup)
- close_mongo_connection(): cleanly close the client (call on shutdown)
- get_database(): return the active database instance for use in routes/services
- ping_database(): lightweight connectivity check used by the health endpoint
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticDatabase

from config import settings

logger = logging.getLogger("budgetnest.database")


class MongoManager:
    """Holds the Motor client/database instances for the app's lifetime."""

    client: AsyncIOMotorClient | None = None
    database: AgnosticDatabase | None = None


mongo_manager = MongoManager()


async def connect_to_mongo() -> None:
    """
    Initialize the Motor client and verify the connection with a ping.
    Intended to be called once, during application startup.
    """
    logger.info("Connecting to MongoDB...")
    # tz_aware=True so datetimes read back from MongoDB (e.g. the OTP
    # expires_at/last_sent_at fields) come back as timezone-aware UTC
    # datetimes. Without this, Motor returns naive datetimes, which
    # cannot be compared against datetime.now(timezone.utc) and raises
    # "can't compare offset-naive and offset-aware datetimes".
    mongo_manager.client = AsyncIOMotorClient(settings.MONGO_URL, tz_aware=True)
    mongo_manager.database = mongo_manager.client[settings.DB_NAME]

    # Verify the connection actually works rather than assuming success,
    # since AsyncIOMotorClient() itself does not raise on a bad URL.
    await mongo_manager.client.admin.command("ping")
    logger.info("MongoDB connection established (db='%s').", settings.DB_NAME)


async def close_mongo_connection() -> None:
    """Close the Motor client cleanly. Intended for application shutdown."""
    if mongo_manager.client is not None:
        mongo_manager.client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AgnosticDatabase:
    """
    Dependency-friendly accessor for the active database instance.
    Raises if called before connect_to_mongo() has run.
    """
    if mongo_manager.database is None:
        raise RuntimeError(
            "Database has not been initialized yet. "
            "Ensure connect_to_mongo() runs during application startup."
        )
    return mongo_manager.database


async def ping_database() -> bool:
    """
    Lightweight connectivity check used by the /api/health endpoint.
    Returns True if MongoDB responds, False otherwise (never raises).
    """
    try:
        if mongo_manager.client is None:
            return False
        await mongo_manager.client.admin.command("ping")
        return True
    except Exception as exc:  # noqa: BLE001 - health check must not crash the app
        logger.warning("MongoDB ping failed: %s", exc)
        return False
