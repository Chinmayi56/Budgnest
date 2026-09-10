"""
services/financial_service.py

Centralized data-access + calculation layer for BudgetNest's core
personal financial engine (starting balance, transactions, balance
calculation, and daily/monthly summaries).

This is the single source of truth for financial math: routes never
compute totals themselves, they call into this module. Every function
here that touches transaction/starting-balance data requires an
explicit user_id and scopes its MongoDB query to it — callers
(routes/finance.py, routes/transactions.py) must always pass the id
of the authenticated user from the validated JWT, never one supplied
by the client.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.core import AgnosticDatabase

from models.transaction import (
    DECREASING_TYPES,
    STARTING_BALANCES_COLLECTION,
    TRANSACTIONS_COLLECTION,
    AdjustmentDirection,
    PaymentMethod,
    TransactionStatus,
    TransactionType,
    new_starting_balance_document,
    new_transaction_document,
    signed_effect,
    starting_balance_doc_to_dict,
    transaction_doc_to_dict,
)
from utils.money import from_decimal128, quantize_amount, to_decimal128

ZERO = Decimal("0.00")


async def ensure_indexes(db: AgnosticDatabase) -> None:
    """Create required indexes for the financial collections. Safe to call every startup."""
    await db[TRANSACTIONS_COLLECTION].create_index("user_id")
    await db[TRANSACTIONS_COLLECTION].create_index("transaction_date")
    await db[TRANSACTIONS_COLLECTION].create_index("transaction_type")
    await db[TRANSACTIONS_COLLECTION].create_index("category")
    await db[TRANSACTIONS_COLLECTION].create_index("status")
    await db[STARTING_BALANCES_COLLECTION].create_index("user_id", unique=True)


def _object_id(raw_id: str) -> Optional[ObjectId]:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError):
        return None


# ---------------------------------------------------------------------
# Starting balance
# ---------------------------------------------------------------------


async def get_starting_balance_doc(db: AgnosticDatabase, user_id: str) -> Optional[dict[str, Any]]:
    return await db[STARTING_BALANCES_COLLECTION].find_one({"user_id": user_id})


async def get_starting_balance_amount(db: AgnosticDatabase, user_id: str) -> Decimal:
    doc = await get_starting_balance_doc(db, user_id)
    if doc is None:
        return ZERO
    return from_decimal128(doc["amount"])


async def create_starting_balance(
    db: AgnosticDatabase, user_id: str, amount: Decimal, balance_date: date, notes: Optional[str]
) -> dict[str, Any]:
    """
    Create the user's starting balance. Raises ValueError if one
    already exists — callers should translate that into a 409 telling
    the client to use the adjustment endpoint instead (see
    adjust_starting_balance).
    """
    existing = await get_starting_balance_doc(db, user_id)
    if existing is not None:
        raise ValueError("starting_balance_already_exists")

    document = new_starting_balance_document(user_id=user_id, amount=amount, balance_date=balance_date, notes=notes)
    result = await db[STARTING_BALANCES_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def adjust_starting_balance(
    db: AgnosticDatabase, user_id: str, amount: Decimal, notes: Optional[str]
) -> Optional[dict[str, Any]]:
    """Explicit adjustment mechanism for an already-established starting balance. Returns None if none exists yet."""
    existing = await get_starting_balance_doc(db, user_id)
    if existing is None:
        return None

    now = datetime.now(timezone.utc)
    update = {"amount": to_decimal128(amount), "updated_at": now}
    if notes is not None:
        update["notes"] = notes.strip() or None

    await db[STARTING_BALANCES_COLLECTION].update_one({"user_id": user_id}, {"$set": update})
    return await get_starting_balance_doc(db, user_id)


# ---------------------------------------------------------------------
# Transactions — CRUD
# ---------------------------------------------------------------------


async def create_transaction(
    db: AgnosticDatabase,
    user_id: str,
    transaction_type: TransactionType,
    amount: Decimal,
    transaction_date: date,
    status: TransactionStatus,
    category: Optional[str] = None,
    description: Optional[str] = None,
    person_name: Optional[str] = None,
    payment_method: Optional[PaymentMethod] = None,
    adjustment_direction: Optional[AdjustmentDirection] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    document = new_transaction_document(
        user_id=user_id,
        transaction_type=transaction_type,
        amount=quantize_amount(amount),
        transaction_date=transaction_date,
        status=status,
        category=category,
        description=description,
        person_name=person_name,
        payment_method=payment_method,
        adjustment_direction=adjustment_direction,
        notes=notes,
    )
    result = await db[TRANSACTIONS_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def get_transaction_for_user(db: AgnosticDatabase, user_id: str, transaction_id: str) -> Optional[dict[str, Any]]:
    """Fetch a transaction by id, scoped to the owning user. Returns None if missing OR owned by someone else."""
    object_id = _object_id(transaction_id)
    if object_id is None:
        return None
    return await db[TRANSACTIONS_COLLECTION].find_one({"_id": object_id, "user_id": user_id})


async def list_transactions_for_user(
    db: AgnosticDatabase,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    transaction_type: Optional[TransactionType] = None,
    category: Optional[str] = None,
    status: Optional[TransactionStatus] = None,
    payment_method: Optional[PaymentMethod] = None,
    person_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> tuple[list[dict[str, Any]], int]:
    query: dict[str, Any] = {"user_id": user_id}
    if transaction_type is not None:
        query["transaction_type"] = transaction_type.value
    if category is not None:
        query["category"] = category.strip().upper()
    if status is not None:
        query["status"] = status.value
    if payment_method is not None:
        query["payment_method"] = payment_method.value
    if person_name is not None:
        query["person_name"] = person_name.strip()
    if start_date is not None or end_date is not None:
        date_filter: dict[str, Any] = {}
        if start_date is not None:
            date_filter["$gte"] = start_date.isoformat()
        if end_date is not None:
            date_filter["$lte"] = end_date.isoformat()
        query["transaction_date"] = date_filter

    total = await db[TRANSACTIONS_COLLECTION].count_documents(query)

    skip = max(page - 1, 0) * page_size
    cursor = (
        db[TRANSACTIONS_COLLECTION]
        .find(query)
        .sort("transaction_date", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = [doc async for doc in cursor]
    return docs, total


async def update_transaction(
    db: AgnosticDatabase,
    user_id: str,
    transaction_id: str,
    changes: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Apply a partial update to a transaction the user owns.

    Safety note (spec section 11): editing a COMPLETED transaction's
    amount/type/status is allowed here (the financial totals are
    always *recomputed live* from current transaction data in
    calculate_summary/daily/monthly rather than from any cached
    running total), so there is no separate ledger to silently
    corrupt. Returns None if the transaction doesn't exist or isn't
    owned by this user.
    """
    existing = await get_transaction_for_user(db, user_id, transaction_id)
    if existing is None:
        return None

    update: dict[str, Any] = {}
    for field, value in changes.items():
        if value is None:
            continue
        if field == "amount":
            update[field] = to_decimal128(value)
        elif field in ("transaction_type", "status", "payment_method", "adjustment_direction"):
            update[field] = value.value if hasattr(value, "value") else value
        elif field == "transaction_date":
            update[field] = value.isoformat()
        elif field == "category":
            update[field] = value.strip().upper() if value else None
        elif field in ("description", "person_name", "notes"):
            update[field] = value.strip() if value else None
        else:
            update[field] = value

    if not update:
        return existing

    update["updated_at"] = datetime.now(timezone.utc)
    await db[TRANSACTIONS_COLLECTION].update_one({"_id": existing["_id"]}, {"$set": update})
    return await get_transaction_for_user(db, user_id, transaction_id)


async def cancel_transaction(db: AgnosticDatabase, user_id: str, transaction_id: str) -> Optional[dict[str, Any]]:
    """
    Soft-delete/reverse a transaction by marking it CANCELLED, instead
    of hard-deleting it, so financial history stays reliable (spec
    section 12). Returns None if the transaction doesn't exist or
    isn't owned by this user.
    """
    return await update_transaction(db, user_id, transaction_id, {"status": TransactionStatus.CANCELLED})


# ---------------------------------------------------------------------
# Balance / summary calculations
# ---------------------------------------------------------------------


def _bucket_totals() -> dict[str, Decimal]:
    return {
        "total_income": ZERO,
        "total_expenses": ZERO,
        "total_payments": ZERO,
        "total_money_given": ZERO,
        "total_money_returned": ZERO,
        "total_refunds": ZERO,
        "total_adjustments": ZERO,
    }


_TYPE_TO_BUCKET = {
    TransactionType.INCOME: "total_income",
    TransactionType.EXPENSE: "total_expenses",
    TransactionType.PAYMENT: "total_payments",
    TransactionType.MONEY_GIVEN: "total_money_given",
    TransactionType.MONEY_RETURNED: "total_money_returned",
    TransactionType.REFUND: "total_refunds",
    TransactionType.ADJUSTMENT: "total_adjustments",
}


async def calculate_summary(db: AgnosticDatabase, user_id: str) -> dict[str, Decimal]:
    """
    Compute the authoritative financial summary for a user, straight
    from current MongoDB data (never hard-coded, never cached).

    Only COMPLETED transactions affect current_balance. PENDING
    transactions with a balance-decreasing type (EXPENSE/PAYMENT/
    MONEY_GIVEN) are treated as upcoming committed amounts and are
    subtracted separately to produce available_balance, while
    current_balance itself stays untouched by them.
    """
    starting_balance = await get_starting_balance_amount(db, user_id)
    totals = _bucket_totals()
    balance_delta = ZERO
    pending_commitments = ZERO

    cursor = db[TRANSACTIONS_COLLECTION].find({"user_id": user_id})
    async for doc in cursor:
        tx_type = TransactionType(doc["transaction_type"])
        status = TransactionStatus(doc["status"])
        amount = from_decimal128(doc["amount"])
        direction = AdjustmentDirection(doc["adjustment_direction"]) if doc.get("adjustment_direction") else None

        if status == TransactionStatus.COMPLETED:
            totals[_TYPE_TO_BUCKET[tx_type]] += amount
            balance_delta += signed_effect(tx_type, amount, direction)
        elif status == TransactionStatus.PENDING and tx_type in DECREASING_TYPES:
            pending_commitments += amount
        # CANCELLED transactions never affect any total.

    current_balance = quantize_amount(starting_balance + balance_delta)
    available_balance = quantize_amount(current_balance - pending_commitments)

    return {
        "starting_balance": starting_balance,
        **totals,
        "current_balance": current_balance,
        "pending_commitments": quantize_amount(pending_commitments),
        "available_balance": available_balance,
    }


async def _period_totals(db: AgnosticDatabase, user_id: str, start: date, end: date) -> dict[str, Any]:
    """
    Shared helper for daily/monthly summaries: totals for COMPLETED
    transactions with transaction_date in [start, end] inclusive.
    """
    totals = _bucket_totals()
    categories: dict[str, Decimal] = {}
    transaction_count = 0

    query = {
        "user_id": user_id,
        "status": TransactionStatus.COMPLETED.value,
        "transaction_date": {"$gte": start.isoformat(), "$lte": end.isoformat()},
    }
    cursor = db[TRANSACTIONS_COLLECTION].find(query)
    async for doc in cursor:
        tx_type = TransactionType(doc["transaction_type"])
        amount = from_decimal128(doc["amount"])
        totals[_TYPE_TO_BUCKET[tx_type]] += amount
        transaction_count += 1

        category = doc.get("category") or "OTHER"
        categories[category] = categories.get(category, ZERO) + amount

    return {
        **totals,
        "transaction_count": transaction_count,
        "categories": categories,
    }


async def calculate_daily_summary(db: AgnosticDatabase, user_id: str, target_date: date) -> dict[str, Any]:
    result = await _period_totals(db, user_id, target_date, target_date)
    return {"date": target_date.isoformat(), **result}


async def calculate_monthly_summary(db: AgnosticDatabase, user_id: str, month: int, year: int) -> dict[str, Any]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1)
        end = date.fromordinal(end.toordinal() - 1)

    result = await _period_totals(db, user_id, start, end)
    return {"month": month, "year": year, **result}
