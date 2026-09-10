"""
services/money_given_service.py

Data-access + calculation layer for STEP 5 "Money Given & Money
Returned" tracking.

IMPORTANT — single source of truth for balance-affecting data:
Creating a money-given record or recording a return never adjusts any
balance itself. It calls Step 3's services.financial_service.create_transaction
to create exactly one real transaction (MONEY_GIVEN or
MONEY_RETURNED) per financial event — the same transactions
collection and the same balance math used everywhere else in
BudgetNest. money_given/money_returns documents only track the
lending *relationship* (who, how much, outstanding, status); they are
never a second, competing source of balance totals. See
models/money_given.py for the full double-counting-prevention note.

Every function here that touches money_given/money_returns data
requires an explicit user_id and scopes its MongoDB query to it —
callers (routes/money_given.py) must always pass the id of the
authenticated user from the validated JWT, never one supplied by the
client.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.core import AgnosticDatabase

from models.money_given import (
    MONEY_GIVEN_COLLECTION,
    MONEY_RETURNS_COLLECTION,
    MoneyGivenCategory,
    MoneyGivenStatus,
    ZERO,
    money_given_doc_to_dict,
    new_money_given_document,
    new_money_return_document,
    status_for_amounts,
)
from models.transaction import PaymentMethod, TransactionStatus, TransactionType
from services import financial_service
from utils.money import from_decimal128, quantize_amount, to_decimal128


async def ensure_indexes(db: AgnosticDatabase) -> None:
    """Create required indexes for the money_given/money_returns collections. Safe to call every startup."""
    await db[MONEY_GIVEN_COLLECTION].create_index("user_id")
    await db[MONEY_GIVEN_COLLECTION].create_index("status")
    await db[MONEY_GIVEN_COLLECTION].create_index("person_name")
    await db[MONEY_GIVEN_COLLECTION].create_index("given_date")
    await db[MONEY_GIVEN_COLLECTION].create_index([("user_id", 1), ("status", 1), ("given_date", -1)])
    await db[MONEY_RETURNS_COLLECTION].create_index("money_given_id")
    await db[MONEY_RETURNS_COLLECTION].create_index("user_id")


def _object_id(raw_id: str) -> Optional[ObjectId]:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError):
        return None


# ---------------------------------------------------------------------
# Money given — CRUD
# ---------------------------------------------------------------------


async def create_money_given(
    db: AgnosticDatabase,
    user_id: str,
    person_name: str,
    amount: Decimal,
    given_date: date,
    reason: Optional[str] = None,
    category: Optional[MoneyGivenCategory] = None,
    payment_method: Optional[PaymentMethod] = None,
    expected_return_date: Optional[date] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a money-given record and, in the same operation, the single
    COMPLETED MONEY_GIVEN transaction that represents its effect on
    the user's Step 3 balance (spec sections 4 and 16).
    """
    amount = quantize_amount(amount)

    transaction_doc = await financial_service.create_transaction(
        db,
        user_id=user_id,
        transaction_type=TransactionType.MONEY_GIVEN,
        amount=amount,
        transaction_date=given_date,
        status=TransactionStatus.COMPLETED,
        category=category.value if category else None,
        description=reason or f"Money given to {person_name.strip()}",
        person_name=person_name,
        payment_method=payment_method,
        notes=notes,
    )

    document = new_money_given_document(
        user_id=user_id,
        person_name=person_name,
        amount_given=amount,
        given_date=given_date,
        given_transaction_id=str(transaction_doc["_id"]),
        reason=reason,
        category=category,
        payment_method=payment_method.value if payment_method else None,
        expected_return_date=expected_return_date,
        notes=notes,
    )
    result = await db[MONEY_GIVEN_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def get_money_given_for_user(db: AgnosticDatabase, user_id: str, money_given_id: str) -> Optional[dict[str, Any]]:
    """Fetch a money-given record by id, scoped to the owning user. Returns None if missing OR owned by someone else."""
    object_id = _object_id(money_given_id)
    if object_id is None:
        return None
    return await db[MONEY_GIVEN_COLLECTION].find_one({"_id": object_id, "user_id": user_id})


async def list_money_given_for_user(
    db: AgnosticDatabase,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    person_name: Optional[str] = None,
    status: Optional[MoneyGivenStatus] = None,
    category: Optional[MoneyGivenCategory] = None,
    payment_method: Optional[PaymentMethod] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> tuple[list[dict[str, Any]], int]:
    query: dict[str, Any] = {"user_id": user_id}
    if person_name is not None:
        query["person_name"] = person_name.strip()
    if status is not None:
        query["status"] = status.value
    if category is not None:
        query["category"] = category.value
    if payment_method is not None:
        query["payment_method"] = payment_method.value
    if start_date is not None or end_date is not None:
        date_filter: dict[str, Any] = {}
        if start_date is not None:
            date_filter["$gte"] = start_date.isoformat()
        if end_date is not None:
            date_filter["$lte"] = end_date.isoformat()
        query["given_date"] = date_filter

    total = await db[MONEY_GIVEN_COLLECTION].count_documents(query)

    skip = max(page - 1, 0) * page_size
    cursor = (
        db[MONEY_GIVEN_COLLECTION]
        .find(query)
        .sort("given_date", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = [doc async for doc in cursor]
    return docs, total


async def update_money_given(
    db: AgnosticDatabase,
    user_id: str,
    money_given_id: str,
    changes: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Apply a safe metadata-only update (spec section 11):
    person_name, reason, category, expected_return_date, notes.

    amount_given/amount_returned/outstanding_amount/status are never
    accepted here — they only ever change through create_money_given
    and add_return, which keep them consistent with the linked Step 3
    transactions. Returns None if the record doesn't exist or isn't
    owned by this user.
    """
    existing = await get_money_given_for_user(db, user_id, money_given_id)
    if existing is None:
        return None

    update: dict[str, Any] = {}
    for field, value in changes.items():
        if value is None:
            continue
        if field == "category":
            update[field] = value.value if hasattr(value, "value") else value
        elif field == "expected_return_date":
            update[field] = value.isoformat()
        elif field in ("person_name", "reason", "notes"):
            update[field] = value.strip() if value else None
        else:
            # Silently ignore any other field (amounts/status/etc.) rather
            # than letting a client corrupt financial history through
            # this endpoint — those fields are simply not in the request
            # schema, but this keeps the service safe regardless of caller.
            continue

    if not update:
        return existing

    update["updated_at"] = datetime.now(timezone.utc)
    await db[MONEY_GIVEN_COLLECTION].update_one({"_id": existing["_id"]}, {"$set": update})
    return await get_money_given_for_user(db, user_id, money_given_id)


async def cancel_money_given(db: AgnosticDatabase, user_id: str, money_given_id: str) -> Optional[dict[str, Any]]:
    """
    Cancel a money-given record using a safe reversal, never a hard
    delete (spec section 12): the linked MONEY_GIVEN transaction and
    every linked MONEY_RETURNED transaction are marked CANCELLED
    (removing their effect from the Step 3 balance), the money_given
    status becomes CANCELLED, and every money_returns document is left
    in place untouched — full return history is preserved, just no
    longer counted anywhere.

    Returns None if the record doesn't exist or isn't owned by this
    user. Raises ValueError('already_cancelled') if it is already
    CANCELLED.
    """
    existing = await get_money_given_for_user(db, user_id, money_given_id)
    if existing is None:
        return None
    if existing["status"] == MoneyGivenStatus.CANCELLED.value:
        raise ValueError("already_cancelled")

    if existing.get("given_transaction_id"):
        await financial_service.cancel_transaction(db, user_id, existing["given_transaction_id"])

    returns = await list_returns_for_money_given(db, user_id, money_given_id)
    for return_doc in returns:
        if return_doc.get("return_transaction_id"):
            await financial_service.cancel_transaction(db, user_id, return_doc["return_transaction_id"])

    now = datetime.now(timezone.utc)
    await db[MONEY_GIVEN_COLLECTION].update_one(
        {"_id": existing["_id"]},
        {"$set": {"status": MoneyGivenStatus.CANCELLED.value, "updated_at": now}},
    )
    return await get_money_given_for_user(db, user_id, money_given_id)


# ---------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------


async def add_return(
    db: AgnosticDatabase,
    user_id: str,
    money_given_id: str,
    amount: Decimal,
    return_date: date,
    payment_method: Optional[PaymentMethod] = None,
    notes: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Record a return against a money-given record (full or partial —
    spec sections 6-7). Creates exactly one COMPLETED MONEY_RETURNED
    transaction, then updates the running returned/outstanding totals
    and status.

    Returns None if the money-given record doesn't exist or isn't
    owned by this user.
    Raises ValueError('record_not_active') if the record is SETTLED
    or CANCELLED (nothing further can be returned against it).
    Raises ValueError('return_exceeds_outstanding') if amount is
    greater than the current outstanding amount.
    """
    existing = await get_money_given_for_user(db, user_id, money_given_id)
    if existing is None:
        return None
    if existing["status"] in (MoneyGivenStatus.SETTLED.value, MoneyGivenStatus.CANCELLED.value):
        raise ValueError("record_not_active")

    amount = quantize_amount(amount)
    outstanding = from_decimal128(existing["outstanding_amount"])
    if amount > outstanding:
        raise ValueError("return_exceeds_outstanding")

    transaction_doc = await financial_service.create_transaction(
        db,
        user_id=user_id,
        transaction_type=TransactionType.MONEY_RETURNED,
        amount=amount,
        transaction_date=return_date,
        status=TransactionStatus.COMPLETED,
        category=existing.get("category"),
        description=f"Money returned by {existing['person_name']}",
        person_name=existing["person_name"],
        payment_method=payment_method,
        notes=notes,
    )

    return_document = new_money_return_document(
        money_given_id=str(existing["_id"]),
        user_id=user_id,
        amount=amount,
        return_date=return_date,
        return_transaction_id=str(transaction_doc["_id"]),
        payment_method=payment_method.value if payment_method else None,
        notes=notes,
    )
    await db[MONEY_RETURNS_COLLECTION].insert_one(return_document)

    amount_given = from_decimal128(existing["amount_given"])
    new_amount_returned = quantize_amount(from_decimal128(existing["amount_returned"]) + amount)
    new_outstanding = quantize_amount(amount_given - new_amount_returned)
    new_status = status_for_amounts(amount_given, new_amount_returned)

    now = datetime.now(timezone.utc)
    await db[MONEY_GIVEN_COLLECTION].update_one(
        {"_id": existing["_id"]},
        {
            "$set": {
                "amount_returned": to_decimal128(new_amount_returned),
                "outstanding_amount": to_decimal128(new_outstanding),
                "status": new_status.value,
                "updated_at": now,
            }
        },
    )
    return await get_money_given_for_user(db, user_id, money_given_id)


async def list_returns_for_money_given(db: AgnosticDatabase, user_id: str, money_given_id: str) -> list[dict[str, Any]]:
    """Return history for one money-given record, oldest first (spec section 8). Scoped to the owning user."""
    cursor = (
        db[MONEY_RETURNS_COLLECTION]
        .find({"money_given_id": money_given_id, "user_id": user_id})
        .sort("return_date", 1)
    )
    return [doc async for doc in cursor]


# ---------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------


async def get_summary(db: AgnosticDatabase, user_id: str) -> dict[str, Any]:
    """
    Aggregate money-given totals for the authenticated user, computed
    live from current MongoDB data (spec section 13). CANCELLED
    records are excluded from every total — their Step 3 transactions
    were already reversed, so counting them here would misrepresent
    both the lending totals and the currently-outstanding amount.
    """
    total_given = ZERO
    total_returned = ZERO
    active_records = 0
    settled_records = 0

    cursor = db[MONEY_GIVEN_COLLECTION].find({"user_id": user_id, "status": {"$ne": MoneyGivenStatus.CANCELLED.value}})
    async for doc in cursor:
        total_given += from_decimal128(doc["amount_given"])
        total_returned += from_decimal128(doc["amount_returned"])
        if doc["status"] == MoneyGivenStatus.SETTLED.value:
            settled_records += 1
        else:
            active_records += 1

    total_outstanding = quantize_amount(total_given - total_returned)
    return {
        "total_money_given": quantize_amount(total_given),
        "total_money_returned": quantize_amount(total_returned),
        "total_outstanding": total_outstanding,
        "active_records": active_records,
        "settled_records": settled_records,
    }


async def get_person_summary(db: AgnosticDatabase, user_id: str) -> list[dict[str, Any]]:
    """
    Aggregate given/returned/outstanding totals per person for the
    authenticated user (spec section 14). CANCELLED records are
    excluded, same reasoning as get_summary. People are returned in
    descending order of outstanding amount, then alphabetically.
    """
    totals: dict[str, dict[str, Decimal]] = {}

    cursor = db[MONEY_GIVEN_COLLECTION].find({"user_id": user_id, "status": {"$ne": MoneyGivenStatus.CANCELLED.value}})
    async for doc in cursor:
        name = doc["person_name"]
        bucket = totals.setdefault(name, {"total_given": ZERO, "total_returned": ZERO})
        bucket["total_given"] += from_decimal128(doc["amount_given"])
        bucket["total_returned"] += from_decimal128(doc["amount_returned"])

    people = []
    for name, bucket in totals.items():
        given = quantize_amount(bucket["total_given"])
        returned = quantize_amount(bucket["total_returned"])
        outstanding = quantize_amount(given - returned)
        people.append(
            {
                "person_name": name,
                "total_given": given,
                "total_returned": returned,
                "outstanding": outstanding,
            }
        )

    people.sort(key=lambda p: (-p["outstanding"], p["person_name"]))
    return people
