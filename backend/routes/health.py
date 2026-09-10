"""
routes/health.py

Simple health-check endpoint(s). No auth, no business logic —
just confirms the API process is running and reports DB connectivity.
"""

from fastapi import APIRouter

from database import ping_database
from config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    GET /api/health

    Returns a simple JSON payload confirming the BudgetNest backend is
    running, plus a lightweight MongoDB connectivity flag.
    """
    db_connected = await ping_database()

    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "BudgetNest backend is running",
        "database_connected": db_connected,
    }
