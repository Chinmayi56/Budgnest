"""
routes/money_given.py

STEP 5 "Money Given & Money Returned" endpoints:
    POST   /api/money-given
    GET    /api/money-given
    GET    /api/money-given/summary
    GET    /api/money-given/person-summary
    GET    /api/money-given/{money_given_id}
    PATCH  /api/money-given/{money_given_id}
    DELETE /api/money-given/{money_given_id}          (cancellation, not a hard delete)
    POST   /api/money-given/{money_given_id}/return
    GET    /api/money-given/{money_given_id}/returns

Every route resolves the acting user from the validated JWT
(get_current_user) and scopes every MongoDB query to that user's id,
exactly like the Step 3 finance/transactions routes and the Step 4
bills routes — a user_id is never accepted from the client, so one
user can never view, list, update, return against, cancel, or
summarize another user's money-given records (returns 404, not 403,
so existence isn't leaked either).

Creating a record or recording a return never computes balance
itself: both delegate to services/money_given_service.py, which calls
Step 3's services/financial_service.create_transaction — the single
source of truth for balance-affecting data.

NOTE: /summary and /person-summary and /{id} all sit at the same
path depth, so the two literal summary routes are declared before the
{money_given_id} routes — otherwise FastAPI would try to parse
"summary" as a money_given_id.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.core import AgnosticDatabase

from database import get_database
from models.money_given import MoneyGivenCategory, MoneyGivenStatus, money_given_doc_to_dict, money_return_doc_to_dict
from models.transaction import PaymentMethod
from schemas.money_given import (
    MoneyGivenCreateRequest,
    MoneyGivenListResponse,
    MoneyGivenPublic,
    MoneyGivenSummaryResponse,
    MoneyGivenUpdateRequest,
    MoneyReturnListResponse,
    MoneyReturnPublic,
    MoneyReturnRequest,
    PersonSummaryItem,
    PersonSummaryResponse,
)
from schemas.user import UserPublic
from services import money_given_service
from utils.deps import get_current_user

logger = logging.getLogger("budgetnest.money_given")

router = APIRouter(prefix="/money-given", tags=["Money Given & Returned"])


@router.post(
    "",
    response_model=MoneyGivenPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Record money given to another person",
)
async def create_money_given(
    payload: MoneyGivenCreateRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    Creates the money-given record and, in the same operation, a real
    COMPLETED MONEY_GIVEN transaction through the Step 3 financial
    engine (so it immediately affects current_balance/summaries).
    Initial amount_returned is 0, initial outstanding_amount equals
    the full amount, and initial status is OUTSTANDING.
    """
    doc = await money_given_service.create_money_given(
        db,
        user_id=current_user.id,
        person_name=payload.person_name,
        amount=payload.amount,
        given_date=payload.given_date,
        reason=payload.reason,
        category=payload.category,
        payment_method=payload.payment_method,
        expected_return_date=payload.expected_return_date,
        notes=payload.notes,
    )
    logger.info("Money-given record created for user %s: %s", current_user.id, payload.person_name)
    return MoneyGivenPublic(**money_given_doc_to_dict(doc))


@router.get(
    "",
    response_model=MoneyGivenListResponse,
    summary="List the authenticated user's money-given records",
)
async def list_money_given(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    person_name: Optional[str] = None,
    status_: Optional[MoneyGivenStatus] = Query(default=None, alias="status"),
    category: Optional[MoneyGivenCategory] = None,
    payment_method: Optional[PaymentMethod] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    docs, total = await money_given_service.list_money_given_for_user(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        person_name=person_name,
        status=status_,
        category=category,
        payment_method=payment_method,
        start_date=start_date,
        end_date=end_date,
    )
    return MoneyGivenListResponse(
        items=[MoneyGivenPublic(**money_given_doc_to_dict(doc)) for doc in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/summary",
    response_model=MoneyGivenSummaryResponse,
    summary="Get the authenticated user's overall money-given/returned/outstanding totals",
)
async def read_summary(
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    summary = await money_given_service.get_summary(db, current_user.id)
    return MoneyGivenSummaryResponse(**summary)


@router.get(
    "/person-summary",
    response_model=PersonSummaryResponse,
    summary="Get the authenticated user's money-given totals aggregated per person",
)
async def read_person_summary(
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    people = await money_given_service.get_person_summary(db, current_user.id)
    return PersonSummaryResponse(people=[PersonSummaryItem(**person) for person in people])


@router.get(
    "/{money_given_id}",
    response_model=MoneyGivenPublic,
    summary="Get a single money-given record, including its return history",
)
async def read_money_given(
    money_given_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await money_given_service.get_money_given_for_user(db, current_user.id, money_given_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Money-given record not found")
    returns = await money_given_service.list_returns_for_money_given(db, current_user.id, money_given_id)
    body = money_given_doc_to_dict(doc)
    body["returns"] = [MoneyReturnPublic(**money_return_doc_to_dict(r)) for r in returns]
    return MoneyGivenPublic(**body)


@router.patch(
    "/{money_given_id}",
    response_model=MoneyGivenPublic,
    summary="Update a money-given record's metadata",
)
async def update_money_given(
    money_given_id: str,
    payload: MoneyGivenUpdateRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    Safe metadata-only update: person_name, reason, category,
    expected_return_date, notes. Financial amounts and status can
    never be changed here — see POST .../return and DELETE (cancel).
    """
    changes = payload.model_dump(exclude_unset=True)
    doc = await money_given_service.update_money_given(db, current_user.id, money_given_id, changes)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Money-given record not found")
    return MoneyGivenPublic(**money_given_doc_to_dict(doc))


@router.delete(
    "/{money_given_id}",
    response_model=MoneyGivenPublic,
    summary="Cancel a money-given record (safe reversal — not a hard delete)",
)
async def cancel_money_given(
    money_given_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    BudgetNest never hard-deletes financial history — see README
    'Deletion / Cancellation Policy'. This reverses the linked Step 3
    MONEY_GIVEN transaction (and every linked MONEY_RETURNED
    transaction) by marking them CANCELLED, sets this record's status
    to CANCELLED, and leaves every return document in place so the
    history remains visible even though it no longer affects any
    total.
    """
    try:
        doc = await money_given_service.cancel_money_given(db, current_user.id, money_given_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This money-given record is already cancelled")
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Money-given record not found")
    return MoneyGivenPublic(**money_given_doc_to_dict(doc))


@router.post(
    "/{money_given_id}/return",
    response_model=MoneyGivenPublic,
    summary="Record a (full or partial) return against a money-given record",
)
async def add_return(
    money_given_id: str,
    payload: MoneyReturnRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    Creates a real COMPLETED MONEY_RETURNED transaction through the
    Step 3 financial engine for this return, then updates the running
    amount_returned/outstanding_amount and automatically recalculates
    status (PARTIALLY_RETURNED while outstanding_amount > 0, SETTLED
    once it reaches zero). Multiple returns are supported — call this
    endpoint again for each further partial return.
    """
    try:
        doc = await money_given_service.add_return(
            db,
            user_id=current_user.id,
            money_given_id=money_given_id,
            amount=payload.amount,
            return_date=payload.return_date,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
    except ValueError as exc:
        if str(exc) == "return_exceeds_outstanding":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Return amount cannot exceed the current outstanding amount",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This money-given record is not active (it is already SETTLED or CANCELLED)",
        )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Money-given record not found")
    return MoneyGivenPublic(**money_given_doc_to_dict(doc))


@router.get(
    "/{money_given_id}/returns",
    response_model=MoneyReturnListResponse,
    summary="Get the return history for a single money-given record",
)
async def read_returns(
    money_given_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    existing = await money_given_service.get_money_given_for_user(db, current_user.id, money_given_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Money-given record not found")
    returns = await money_given_service.list_returns_for_money_given(db, current_user.id, money_given_id)
    return MoneyReturnListResponse(items=[MoneyReturnPublic(**money_return_doc_to_dict(r)) for r in returns])
