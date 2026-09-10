"""
routes/bills.py

STEP 4 Payment/Bill endpoints (recurring + one-off scheduled
payments):
    POST   /api/bills
    GET    /api/bills
    GET    /api/bills/upcoming
    GET    /api/bills/{bill_id}
    PATCH  /api/bills/{bill_id}
    DELETE /api/bills/{bill_id}          (cancellation, not a hard delete)
    POST   /api/bills/{bill_id}/pay

Every route resolves the acting user from the validated JWT
(get_current_user) and scopes every MongoDB query to that user's id,
exactly like the Step 3 finance/transactions routes.

Marking a bill paid never computes balance itself: it delegates to
services/bill_service.pay_bill, which calls Step 3's
services/financial_service.create_transaction — the single source of
truth for balance-affecting data.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.core import AgnosticDatabase

from database import get_database
from models.bill import BillStatus, bill_doc_to_dict
from schemas.bill import (
    BillCreateRequest,
    BillListResponse,
    BillPayRequest,
    BillPublic,
    BillUpdateRequest,
    MonthlyUpcomingTotalResponse,
    PaymentSummaryResponse,
)
from schemas.user import UserPublic
from services import bill_service
from utils.deps import get_current_user

logger = logging.getLogger("budgetnest.bills")

router = APIRouter(prefix="/bills", tags=["Bills & Payments"])


@router.post(
    "",
    response_model=BillPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recurring or one-off scheduled payment (bill)",
)
async def create_bill(
    payload: BillCreateRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await bill_service.create_bill(
        db,
        user_id=current_user.id,
        name=payload.name,
        amount=payload.amount,
        due_date=payload.due_date,
        is_recurring=payload.is_recurring,
        frequency=payload.frequency,
        category=payload.category,
        payment_method=payload.payment_method,
        person_name=payload.person_name,
        notes=payload.notes,
        description=payload.description,
        priority=payload.priority,
        reminder_enabled=payload.reminder_enabled,
        reminder_date=payload.reminder_date,
    )
    logger.info("Bill created for user %s: %s (recurring=%s)", current_user.id, payload.name, payload.is_recurring)
    return BillPublic(**bill_doc_to_dict(doc))


@router.get(
    "",
    response_model=BillListResponse,
    summary="List the authenticated user's bills",
)
async def list_bills(
    status_: Optional[BillStatus] = Query(default=None, alias="status"),
    is_recurring: Optional[bool] = None,
    category: Optional[str] = None,
    due_before: Optional[date] = None,
    due_after: Optional[date] = None,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    docs = await bill_service.list_bills_for_user(
        db,
        user_id=current_user.id,
        status=status_,
        is_recurring=is_recurring,
        category=category,
        due_before=due_before,
        due_after=due_after,
    )
    return BillListResponse(items=[BillPublic(**bill_doc_to_dict(doc)) for doc in docs])


@router.get(
    "/upcoming",
    response_model=BillListResponse,
    summary="List ACTIVE bills due within the next N days",
)
async def list_upcoming_bills(
    days: int = Query(default=30, ge=1, le=365),
    category: Optional[str] = None,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    docs = await bill_service.list_upcoming_bills(db, current_user.id, within_days=days, category=category)
    return BillListResponse(items=[BillPublic(**bill_doc_to_dict(doc)) for doc in docs])


@router.get(
    "/overdue",
    response_model=BillListResponse,
    summary="List the authenticated user's overdue bills",
)
async def list_overdue_bills(
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    docs = await bill_service.list_overdue_bills(db, current_user.id)
    return BillListResponse(items=[BillPublic(**bill_doc_to_dict(doc)) for doc in docs])


@router.get(
    "/summary",
    response_model=PaymentSummaryResponse,
    summary="Get upcoming/due/overdue/paid counts and amounts",
)
async def read_payment_summary(
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    summary = await bill_service.get_payment_summary(db, current_user.id)
    return PaymentSummaryResponse(**summary)


@router.get(
    "/monthly-upcoming",
    response_model=MonthlyUpcomingTotalResponse,
    summary="Total of ACTIVE bills due within a given month (not actual spending)",
)
async def read_monthly_upcoming_total(
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2000, le=2100),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    today = date.today()
    resolved_month = month or today.month
    resolved_year = year or today.year
    result = await bill_service.get_monthly_upcoming_total(db, current_user.id, resolved_month, resolved_year)
    return MonthlyUpcomingTotalResponse(**result)


@router.get(
    "/{bill_id}",
    response_model=BillPublic,
    summary="Get a single bill",
)
async def read_bill(
    bill_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await bill_service.get_bill_for_user(db, current_user.id, bill_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return BillPublic(**bill_doc_to_dict(doc))


@router.patch(
    "/{bill_id}",
    response_model=BillPublic,
    summary="Update a bill's schedule/details",
)
async def update_bill(
    bill_id: str,
    payload: BillUpdateRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    changes = payload.model_dump(exclude_unset=True)
    doc = await bill_service.update_bill(db, current_user.id, bill_id, changes)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return BillPublic(**bill_doc_to_dict(doc))


@router.delete(
    "/{bill_id}",
    response_model=BillPublic,
    summary="Cancel a bill (soft delete — stops future scheduling)",
)
async def cancel_bill(
    bill_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await bill_service.cancel_bill(db, current_user.id, bill_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return BillPublic(**bill_doc_to_dict(doc))


@router.post(
    "/{bill_id}/pay",
    response_model=BillPublic,
    summary="Mark a bill as paid — creates a real PAYMENT transaction",
)
async def pay_bill(
    bill_id: str,
    payload: BillPayRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    Creates a COMPLETED PAYMENT transaction for this bill's amount
    through the Step 3 financial engine (so it immediately affects
    current_balance/summaries), then advances the bill's due_date
    (recurring) or marks it COMPLETED (one-off).
    """
    try:
        doc = await bill_service.pay_bill(
            db, current_user.id, bill_id, payment_date=payload.payment_date, notes=payload.notes
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This bill is not ACTIVE (it may be paused, cancelled, or already completed).",
        )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return BillPublic(**bill_doc_to_dict(doc))
