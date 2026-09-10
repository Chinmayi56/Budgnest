"""
routes/budgets.py

STEP 4 personal budget endpoints:
    POST   /api/budgets
    GET    /api/budgets
    GET    /api/budgets/{budget_id}
    PATCH  /api/budgets/{budget_id}
    DELETE /api/budgets/{budget_id}

Every route resolves the acting user from the validated JWT
(get_current_user) and scopes every MongoDB query to that user's id —
a user_id is never accepted from the client, exactly like the Step 3
finance/transactions routes.

Spend totals shown against a budget are always computed live from the
existing Step 3 financial engine (services/budget_service.py calls
services/financial_service.calculate_monthly_summary) — this file
does not, and must not, do its own financial arithmetic.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.core import AgnosticDatabase

from database import get_database
from schemas.budget import (
    BudgetCreateRequest,
    BudgetListResponse,
    BudgetPublic,
    BudgetUpdateRequest,
    BudgetWithUsage,
)
from schemas.user import UserPublic
from services import budget_service
from utils.deps import get_current_user

logger = logging.getLogger("budgetnest.budgets")

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post(
    "",
    response_model=BudgetWithUsage,
    status_code=status.HTTP_201_CREATED,
    summary="Create a personal budget (overall or per-category) for a month",
)
async def create_budget(
    payload: BudgetCreateRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    Creates one budget per (type[, category]) per month. If one
    already exists for that month, use PATCH /api/budgets/{budget_id}
    to adjust its limit instead — this prevents accidental duplicate
    budgets, mirroring the starting-balance pattern from Step 3.
    """
    try:
        doc = await budget_service.create_budget(
            db,
            user_id=current_user.id,
            budget_type=payload.budget_type,
            limit_amount=payload.limit_amount,
            month=payload.month,
            year=payload.year,
            category=payload.category,
            notes=payload.notes,
        )
    except ValueError:
        scope = f"category '{payload.category}'" if payload.category else "an overall budget"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A budget for {scope} already exists for {payload.month}/{payload.year}. "
            f"Use PATCH /api/budgets/{{budget_id}} to adjust it.",
        )
    usage = await budget_service.get_budget_usage(db, current_user.id, doc)
    logger.info("Budget created for user %s: %s %s", current_user.id, payload.budget_type.value, payload.category or "OVERALL")
    return BudgetWithUsage(**usage)


@router.get(
    "",
    response_model=BudgetListResponse,
    summary="List the authenticated user's budgets, with live usage",
)
async def list_budgets(
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    usages = await budget_service.get_budgets_with_usage(db, current_user.id, month=month, year=year)
    return BudgetListResponse(items=[BudgetWithUsage(**usage) for usage in usages])


@router.get(
    "/{budget_id}",
    response_model=BudgetWithUsage,
    summary="Get a single budget with live usage",
)
async def read_budget(
    budget_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await budget_service.get_budget_for_user(db, current_user.id, budget_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    usage = await budget_service.get_budget_usage(db, current_user.id, doc)
    return BudgetWithUsage(**usage)


@router.patch(
    "/{budget_id}",
    response_model=BudgetWithUsage,
    summary="Update a budget's limit or notes",
)
async def update_budget(
    budget_id: str,
    payload: BudgetUpdateRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await budget_service.update_budget(
        db, current_user.id, budget_id, limit_amount=payload.limit_amount, notes=payload.notes
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    usage = await budget_service.get_budget_usage(db, current_user.id, doc)
    return BudgetWithUsage(**usage)


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a budget",
)
async def delete_budget(
    budget_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    Budgets are planning configuration, not financial history —
    deleting one never touches the underlying transactions it was
    measured against, so a real delete (unlike transactions) is safe.
    """
    deleted = await budget_service.delete_budget(db, current_user.id, budget_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return None
