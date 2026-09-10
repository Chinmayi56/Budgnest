"""
routes/finance.py

Starting-balance and financial-summary endpoints:
    POST  /api/finance/starting-balance
    GET   /api/finance/starting-balance
    PATCH /api/finance/starting-balance
    GET   /api/finance/summary
    GET   /api/finance/daily-summary
    GET   /api/finance/monthly-summary

Every route resolves the acting user from the validated JWT
(get_current_user) and passes only that user's id into
services/financial_service.py — a user_id is never accepted from
request bodies or query parameters, so one user can never read or
change another user's balance.
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.core import AgnosticDatabase

from database import get_database
from schemas.finance import (
    DailySummaryResponse,
    FinancialSummaryResponse,
    MonthlySummaryResponse,
    StartingBalanceAdjustRequest,
    StartingBalancePublic,
    StartingBalanceRequest,
    SuggestedCategoriesResponse,
)
from schemas.user import UserPublic
from services import financial_service
from models.transaction import starting_balance_doc_to_dict
from utils.deps import get_current_user

logger = logging.getLogger("budgetnest.finance")

router = APIRouter(prefix="/finance", tags=["Personal Finance"])


@router.post(
    "/starting-balance",
    response_model=StartingBalancePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Set the authenticated user's starting balance",
)
async def create_starting_balance(
    payload: StartingBalanceRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    Creates the starting balance exactly once per user. If one already
    exists, use PATCH /api/finance/starting-balance to adjust it
    instead — this prevents accidental duplicate starting balances.
    """
    try:
        doc = await financial_service.create_starting_balance(
            db, user_id=current_user.id, amount=payload.amount, balance_date=payload.date, notes=payload.notes
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A starting balance already exists for this account. Use PATCH /api/finance/starting-balance to adjust it.",
        )
    return StartingBalancePublic(**starting_balance_doc_to_dict(doc))


@router.get(
    "/starting-balance",
    response_model=StartingBalancePublic,
    summary="Get the authenticated user's starting balance",
)
async def read_starting_balance(
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await financial_service.get_starting_balance_doc(db, current_user.id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No starting balance has been set yet")
    return StartingBalancePublic(**starting_balance_doc_to_dict(doc))


@router.patch(
    "/starting-balance",
    response_model=StartingBalancePublic,
    summary="Adjust the authenticated user's starting balance",
)
async def adjust_starting_balance(
    payload: StartingBalanceAdjustRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """The explicit, intentional adjustment mechanism referenced by POST above."""
    doc = await financial_service.adjust_starting_balance(
        db, user_id=current_user.id, amount=payload.amount, notes=payload.notes
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No starting balance exists yet. Use POST /api/finance/starting-balance to create one.",
        )
    return StartingBalancePublic(**starting_balance_doc_to_dict(doc))


@router.get(
    "/summary",
    response_model=FinancialSummaryResponse,
    summary="Get the authenticated user's current financial summary",
)
async def read_summary(
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    summary = await financial_service.calculate_summary(db, current_user.id)
    return FinancialSummaryResponse(**summary)


@router.get(
    "/daily-summary",
    response_model=DailySummaryResponse,
    summary="Get a daily financial summary for the authenticated user",
)
async def read_daily_summary(
    date: date = Query(..., description="Date to summarize, e.g. 2026-08-25"),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    summary = await financial_service.calculate_daily_summary(db, current_user.id, date)
    return DailySummaryResponse(**summary)


@router.get(
    "/monthly-summary",
    response_model=MonthlySummaryResponse,
    summary="Get a monthly financial summary for the authenticated user",
)
async def read_monthly_summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    summary = await financial_service.calculate_monthly_summary(db, current_user.id, month, year)
    return MonthlySummaryResponse(**summary)


@router.get(
    "/categories",
    response_model=SuggestedCategoriesResponse,
    summary="Get the suggested (non-exhaustive) list of personal expense/income categories",
)
async def read_suggested_categories():
    return SuggestedCategoriesResponse()
