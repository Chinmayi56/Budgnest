"""
routes/transactions.py

Unified personal transaction endpoints:
    POST   /api/transactions
    GET    /api/transactions
    GET    /api/transactions/{transaction_id}
    PATCH  /api/transactions/{transaction_id}
    DELETE /api/transactions/{transaction_id}   (cancellation/reversal, not a hard delete)

Every route resolves the acting user from the validated JWT
(get_current_user) and scopes every MongoDB query to that user's id —
a user_id is never accepted from the client, so one user can never
read, list, update, or cancel another user's transactions (returns
404, not 403, so existence isn't leaked either).
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.core import AgnosticDatabase

from database import get_database
from models.transaction import PaymentMethod, TransactionStatus, TransactionType, transaction_doc_to_dict
from schemas.finance import TransactionCreateRequest, TransactionListResponse, TransactionPublic, TransactionUpdateRequest
from schemas.user import UserPublic
from services import financial_service
from utils.deps import get_current_user

logger = logging.getLogger("budgetnest.transactions")

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "",
    response_model=TransactionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a personal transaction",
)
async def create_transaction(
    payload: TransactionCreateRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await financial_service.create_transaction(
        db,
        user_id=current_user.id,
        transaction_type=payload.transaction_type,
        amount=payload.amount,
        transaction_date=payload.transaction_date,
        status=payload.status,
        category=payload.category,
        description=payload.description,
        person_name=payload.person_name,
        payment_method=payload.payment_method,
        adjustment_direction=payload.adjustment_direction,
        notes=payload.notes,
    )
    logger.info("Transaction created for user %s: %s", current_user.id, payload.transaction_type.value)
    return TransactionPublic(**transaction_doc_to_dict(doc))


@router.get(
    "",
    response_model=TransactionListResponse,
    summary="List the authenticated user's transactions",
)
async def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    transaction_type: Optional[TransactionType] = None,
    category: Optional[str] = None,
    status_: Optional[TransactionStatus] = Query(default=None, alias="status"),
    payment_method: Optional[PaymentMethod] = None,
    person_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    docs, total = await financial_service.list_transactions_for_user(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        transaction_type=transaction_type,
        category=category,
        status=status_,
        payment_method=payment_method,
        person_name=person_name,
        start_date=start_date,
        end_date=end_date,
    )
    return TransactionListResponse(
        items=[TransactionPublic(**transaction_doc_to_dict(doc)) for doc in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionPublic,
    summary="Get a single transaction",
)
async def read_transaction(
    transaction_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    doc = await financial_service.get_transaction_for_user(db, current_user.id, transaction_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return TransactionPublic(**transaction_doc_to_dict(doc))


@router.patch(
    "/{transaction_id}",
    response_model=TransactionPublic,
    summary="Update a transaction",
)
async def update_transaction(
    transaction_id: str,
    payload: TransactionUpdateRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    changes = payload.model_dump(exclude_unset=True)

    # Re-validate the adjustment_direction/transaction_type relationship
    # against the *resulting* transaction, not just the fields the
    # client happened to send this call.
    existing = await financial_service.get_transaction_for_user(db, current_user.id, transaction_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    resulting_type = changes.get("transaction_type", existing["transaction_type"])
    resulting_direction = changes.get("adjustment_direction", existing.get("adjustment_direction"))
    is_adjustment = resulting_type == TransactionType.ADJUSTMENT.value or resulting_type == TransactionType.ADJUSTMENT
    if is_adjustment and not resulting_direction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="adjustment_direction is required when transaction_type is ADJUSTMENT",
        )
    if not is_adjustment and resulting_direction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="adjustment_direction is only valid when transaction_type is ADJUSTMENT",
        )

    doc = await financial_service.update_transaction(db, current_user.id, transaction_id, changes)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return TransactionPublic(**transaction_doc_to_dict(doc))


@router.delete(
    "/{transaction_id}",
    response_model=TransactionPublic,
    summary="Cancel a transaction (soft delete / reversal)",
)
async def cancel_transaction(
    transaction_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    """
    BudgetNest never hard-deletes a transaction — see README
    'Deletion / Reversal Policy'. This marks the transaction CANCELLED
    instead, which removes its effect from every balance/summary
    calculation while preserving it in history.
    """
    doc = await financial_service.cancel_transaction(db, current_user.id, transaction_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return TransactionPublic(**transaction_doc_to_dict(doc))
