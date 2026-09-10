"""
services/bill_service.py

Data-access layer for STEP 4 Payment/Bill scheduling (recurring +
one-off scheduled payments).

IMPORTANT — single source of truth for balance-affecting data:
Marking a bill "paid" does not adjust any balance itself. It calls
Step 3's services.financial_service.create_transaction to create a
real PAYMENT transaction — the same transactions collection and the
same balance math used everywhere else in BudgetNest. Bills only
track *schedule* state (due date, recurrence, last-paid marker); they
are never a second, competing source of financial totals.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.core import AgnosticDatabase

from models.bill import (
    BILLS_COLLECTION,
    BillFrequency,
    BillPriority,
    BillStatus,
    DueStatus,
    bill_doc_to_dict,
    compute_due_status,
    new_bill_document,
    next_due_date,
)
from models.transaction import TRANSACTIONS_COLLECTION, PaymentMethod, TransactionStatus, TransactionType
from services import financial_service
from utils.money import from_decimal128, quantize_amount, to_decimal128

ZERO = Decimal("0.00")


async def ensure_indexes(db: AgnosticDatabase) -> None:
    """Create required indexes for the bills collection. Safe to call every startup."""
    await db[BILLS_COLLECTION].create_index("user_id")
    await db[BILLS_COLLECTION].create_index("due_date")
    await db[BILLS_COLLECTION].create_index("status")
    await db[BILLS_COLLECTION].create_index([("user_id", 1), ("status", 1), ("due_date", 1)])


def _object_id(raw_id: str) -> Optional[ObjectId]:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError):
        return None


async def create_bill(
    db: AgnosticDatabase,
    user_id: str,
    name: str,
    amount: Decimal,
    due_date: date,
    is_recurring: bool,
    frequency: Optional[BillFrequency] = None,
    category: Optional[str] = None,
    payment_method: Optional[PaymentMethod] = None,
    person_name: Optional[str] = None,
    notes: Optional[str] = None,
    description: Optional[str] = None,
    priority: BillPriority = BillPriority.MEDIUM,
    reminder_enabled: bool = False,
    reminder_date: Optional[date] = None,
) -> dict[str, Any]:
    document = new_bill_document(
        user_id=user_id,
        name=name,
        amount=amount,
        due_date=due_date,
        is_recurring=is_recurring,
        frequency=frequency,
        category=category,
        payment_method=payment_method.value if payment_method else None,
        person_name=person_name,
        notes=notes,
        description=description,
        priority=priority,
        reminder_enabled=reminder_enabled,
        reminder_date=reminder_date,
    )
    result = await db[BILLS_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def get_bill_for_user(db: AgnosticDatabase, user_id: str, bill_id: str) -> Optional[dict[str, Any]]:
    object_id = _object_id(bill_id)
    if object_id is None:
        return None
    return await db[BILLS_COLLECTION].find_one({"_id": object_id, "user_id": user_id})


async def list_bills_for_user(
    db: AgnosticDatabase,
    user_id: str,
    status: Optional[BillStatus] = None,
    is_recurring: Optional[bool] = None,
    category: Optional[str] = None,
    due_before: Optional[date] = None,
    due_after: Optional[date] = None,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"user_id": user_id}
    if status is not None:
        query["status"] = status.value
    if is_recurring is not None:
        query["is_recurring"] = is_recurring
    if category is not None:
        query["category"] = category.strip().upper()
    if due_before is not None or due_after is not None:
        date_filter: dict[str, Any] = {}
        if due_after is not None:
            date_filter["$gte"] = due_after.isoformat()
        if due_before is not None:
            date_filter["$lte"] = due_before.isoformat()
        query["due_date"] = date_filter

    cursor = db[BILLS_COLLECTION].find(query).sort("due_date", 1)
    return [doc async for doc in cursor]


async def list_upcoming_bills(
    db: AgnosticDatabase,
    user_id: str,
    within_days: int = 30,
    category: Optional[str] = None,
) -> list[dict[str, Any]]:
    """ACTIVE bills due within the next `within_days` days (inclusive), soonest first."""
    today = date.today()
    horizon = today + timedelta(days=within_days)
    return await list_bills_for_user(
        db, user_id, status=BillStatus.ACTIVE, due_before=horizon, due_after=today, category=category
    )


async def list_overdue_bills(db: AgnosticDatabase, user_id: str) -> list[dict[str, Any]]:
    """ACTIVE bills whose due_date has already passed (spec section 7), soonest-overdue first."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    return await list_bills_for_user(db, user_id, status=BillStatus.ACTIVE, due_before=yesterday)


async def update_bill(
    db: AgnosticDatabase,
    user_id: str,
    bill_id: str,
    changes: dict[str, Any],
) -> Optional[dict[str, Any]]:
    existing = await get_bill_for_user(db, user_id, bill_id)
    if existing is None:
        return None

    update: dict[str, Any] = {}
    for field, value in changes.items():
        if value is None:
            continue
        if field == "amount":
            update[field] = to_decimal128(value)
        elif field in ("frequency", "payment_method", "status", "priority"):
            update[field] = value.value if hasattr(value, "value") else value
        elif field in ("due_date", "reminder_date"):
            update[field] = value.isoformat()
        elif field == "category":
            update[field] = value.strip().upper() if value else None
        elif field in ("name", "description", "person_name", "notes"):
            update[field] = value.strip() if value else None
        else:
            update[field] = value

    if not update:
        return existing

    update["updated_at"] = datetime.now(timezone.utc)
    await db[BILLS_COLLECTION].update_one({"_id": existing["_id"]}, {"$set": update})
    return await get_bill_for_user(db, user_id, bill_id)


# ---------------------------------------------------------------------
# STEP 6 — Payment summary / monthly upcoming total
# ---------------------------------------------------------------------


async def get_payment_summary(db: AgnosticDatabase, user_id: str) -> dict[str, Any]:
    """
    Aggregate counts/amounts across all of the user's bills, grouped
    by the computed DueStatus (spec section 13). Every number here
    comes straight from current database data — never hard-coded.

    `paid_count` counts COMPLETED PAYMENT transactions (the real,
    balance-affecting record created every time a bill is paid — see
    pay_bill above) rather than bill documents themselves, since a
    recurring bill only ever keeps its *current* schedule state and
    would otherwise undercount how many times it has actually been
    paid.
    """
    today = date.today()
    counts = {status: 0 for status in (DueStatus.UPCOMING, DueStatus.DUE, DueStatus.OVERDUE)}
    amounts = {status: ZERO for status in (DueStatus.UPCOMING, DueStatus.DUE, DueStatus.OVERDUE)}

    cursor = db[BILLS_COLLECTION].find({"user_id": user_id})
    async for doc in cursor:
        bill_status = BillStatus(doc["status"])
        due_status = compute_due_status(bill_status, doc["due_date"], today)
        if due_status in counts:
            counts[due_status] += 1
            amounts[due_status] += from_decimal128(doc["amount"])

    paid_count = await db[TRANSACTIONS_COLLECTION].count_documents(
        {
            "user_id": user_id,
            "transaction_type": TransactionType.PAYMENT.value,
            "status": TransactionStatus.COMPLETED.value,
        }
    )

    return {
        "upcoming_count": counts[DueStatus.UPCOMING],
        "due_count": counts[DueStatus.DUE],
        "overdue_count": counts[DueStatus.OVERDUE],
        "paid_count": paid_count,
        "upcoming_amount": quantize_amount(amounts[DueStatus.UPCOMING]),
        "due_amount": quantize_amount(amounts[DueStatus.DUE]),
        "overdue_amount": quantize_amount(amounts[DueStatus.OVERDUE]),
    }


async def get_monthly_upcoming_total(db: AgnosticDatabase, user_id: str, month: int, year: int) -> dict[str, Any]:
    """
    Sum of ACTIVE bills due within the given month/year (spec section
    14). This is a purely informational total of *committed upcoming*
    payments — it must never be confused with, or subtracted from,
    the actual current_balance/available_balance computed by
    services/financial_service.py (spec section 17).
    """
    start = date(year, month, 1).isoformat()
    if month == 12:
        end = date(year, 12, 31).isoformat()
    else:
        end = (date(year, month + 1, 1) - timedelta(days=1)).isoformat()

    query = {
        "user_id": user_id,
        "status": BillStatus.ACTIVE.value,
        "due_date": {"$gte": start, "$lte": end},
    }
    cursor = db[BILLS_COLLECTION].find(query).sort("due_date", 1)
    items = []
    total = ZERO
    async for doc in cursor:
        amount = from_decimal128(doc["amount"])
        total += amount
        items.append({"id": str(doc["_id"]), "name": doc["name"], "amount": amount, "due_date": doc["due_date"]})

    return {"month": month, "year": year, "items": items, "total": quantize_amount(total)}


async def cancel_bill(db: AgnosticDatabase, user_id: str, bill_id: str) -> Optional[dict[str, Any]]:
    """Soft-cancel a bill (stop scheduling it) rather than deleting its history."""
    return await update_bill(db, user_id, bill_id, {"status": BillStatus.CANCELLED})


async def pay_bill(
    db: AgnosticDatabase,
    user_id: str,
    bill_id: str,
    payment_date: Optional[date] = None,
    notes: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Mark a bill as paid: creates a real PAYMENT transaction via
    services.financial_service.create_transaction (the single source
    of truth for balance-affecting data), then advances the bill's
    due_date (if recurring) or marks it COMPLETED (if one-off).

    Returns None if the bill doesn't exist / isn't owned by this user.
    Raises ValueError('bill_not_active') if the bill is PAUSED,
    CANCELLED, or already COMPLETED.
    """
    existing = await get_bill_for_user(db, user_id, bill_id)
    if existing is None:
        return None
    if existing["status"] != BillStatus.ACTIVE.value:
        raise ValueError("bill_not_active")

    effective_date = payment_date or date.today()
    amount = from_decimal128(existing["amount"])
    payment_method = PaymentMethod(existing["payment_method"]) if existing.get("payment_method") else None

    transaction_doc = await financial_service.create_transaction(
        db,
        user_id=user_id,
        transaction_type=TransactionType.PAYMENT,
        amount=amount,
        transaction_date=effective_date,
        status=TransactionStatus.COMPLETED,
        category=existing.get("category"),
        description=f"Bill payment: {existing['name']}",
        person_name=existing.get("person_name"),
        payment_method=payment_method,
        notes=notes or existing.get("notes"),
    )

    update: dict[str, Any] = {
        "last_paid_date": effective_date.isoformat(),
        "last_transaction_id": str(transaction_doc["_id"]),
        "updated_at": datetime.now(timezone.utc),
    }

    if existing["is_recurring"] and existing.get("frequency"):
        frequency = BillFrequency(existing["frequency"])
        current_due = date.fromisoformat(existing["due_date"])
        update["due_date"] = next_due_date(current_due, frequency).isoformat()
    else:
        update["status"] = BillStatus.COMPLETED.value

    await db[BILLS_COLLECTION].update_one({"_id": existing["_id"]}, {"$set": update})
    return await get_bill_for_user(db, user_id, bill_id)
