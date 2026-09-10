"""
services/budget_service.py

Data-access + usage-calculation layer for STEP 4 personal budgets
(overall + per-category monthly spending limits).

IMPORTANT — single source of truth for financial math:
This module never recomputes spending totals itself. "How much has
been spent" for a given month/category always comes from Step 3's
services.financial_service.calculate_monthly_summary (total_expenses
for OVERALL budgets, the relevant categories[...] entry for CATEGORY
budgets). Budgets only store *limits*; the Step 3 transaction engine
remains the only place balance/spend math happens.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.core import AgnosticDatabase

from models.budget import (
    BUDGETS_COLLECTION,
    BudgetType,
    budget_doc_to_dict,
    compute_budget_status,
    new_budget_document,
)
from services.financial_service import calculate_monthly_summary
from utils.money import quantize_amount, to_decimal128

ZERO = Decimal("0.00")


async def ensure_indexes(db: AgnosticDatabase) -> None:
    """Create required indexes for the budgets collection. Safe to call every startup."""
    await db[BUDGETS_COLLECTION].create_index("user_id")
    await db[BUDGETS_COLLECTION].create_index([("user_id", 1), ("month", 1), ("year", 1)])
    # One overall budget, and one budget per category, per user per month.
    await db[BUDGETS_COLLECTION].create_index(
        [("user_id", 1), ("month", 1), ("year", 1), ("budget_type", 1), ("category", 1)],
        unique=True,
    )


def _object_id(raw_id: str) -> Optional[ObjectId]:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError):
        return None


async def create_budget(
    db: AgnosticDatabase,
    user_id: str,
    budget_type: BudgetType,
    limit_amount: Decimal,
    month: int,
    year: int,
    category: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a budget. Raises ValueError('budget_already_exists') if a
    budget of the same type (+ category, for CATEGORY budgets) already
    exists for this user/month/year — callers should translate that
    into a 409 telling the client to use PATCH instead.
    """
    normalized_category = category.strip().upper() if category else None
    existing = await db[BUDGETS_COLLECTION].find_one(
        {
            "user_id": user_id,
            "month": month,
            "year": year,
            "budget_type": budget_type.value,
            "category": normalized_category,
        }
    )
    if existing is not None:
        raise ValueError("budget_already_exists")

    document = new_budget_document(
        user_id=user_id,
        budget_type=budget_type,
        limit_amount=limit_amount,
        month=month,
        year=year,
        category=category,
        notes=notes,
    )
    result = await db[BUDGETS_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def get_budget_for_user(db: AgnosticDatabase, user_id: str, budget_id: str) -> Optional[dict[str, Any]]:
    object_id = _object_id(budget_id)
    if object_id is None:
        return None
    return await db[BUDGETS_COLLECTION].find_one({"_id": object_id, "user_id": user_id})


async def list_budgets_for_user(
    db: AgnosticDatabase,
    user_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"user_id": user_id}
    if month is not None:
        query["month"] = month
    if year is not None:
        query["year"] = year
    cursor = db[BUDGETS_COLLECTION].find(query).sort([("year", -1), ("month", -1), ("budget_type", 1)])
    return [doc async for doc in cursor]


async def update_budget(
    db: AgnosticDatabase,
    user_id: str,
    budget_id: str,
    limit_amount: Optional[Decimal] = None,
    notes: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    existing = await get_budget_for_user(db, user_id, budget_id)
    if existing is None:
        return None

    update: dict[str, Any] = {}
    if limit_amount is not None:
        update["limit_amount"] = to_decimal128(limit_amount)
    if notes is not None:
        update["notes"] = notes.strip() or None

    if not update:
        return existing

    update["updated_at"] = datetime.now(timezone.utc)
    await db[BUDGETS_COLLECTION].update_one({"_id": existing["_id"]}, {"$set": update})
    return await get_budget_for_user(db, user_id, budget_id)


async def delete_budget(db: AgnosticDatabase, user_id: str, budget_id: str) -> bool:
    """
    Hard-delete a budget. Unlike transactions, budgets are planning
    configuration rather than financial history, so removing one does
    not corrupt any historical record — the underlying transactions
    that were ever counted against it are untouched.
    """
    existing = await get_budget_for_user(db, user_id, budget_id)
    if existing is None:
        return False
    await db[BUDGETS_COLLECTION].delete_one({"_id": existing["_id"]})
    return True


async def get_budget_usage(db: AgnosticDatabase, user_id: str, budget_doc: dict[str, Any]) -> dict[str, Any]:
    """
    Compute a single budget's spend/remaining/status by pulling
    total_expenses / categories straight from
    financial_service.calculate_monthly_summary — never recomputed
    here.
    """
    base = budget_doc_to_dict(budget_doc)
    monthly = await calculate_monthly_summary(db, user_id, base["month"], base["year"])

    if base["budget_type"] == BudgetType.OVERALL:
        spent = monthly["total_expenses"]
    else:
        spent = monthly["categories"].get(base["category"], ZERO)

    spent = quantize_amount(spent)
    remaining = quantize_amount(base["limit_amount"] - spent)
    percentage_used = float((spent / base["limit_amount"] * 100)) if base["limit_amount"] > 0 else 0.0

    return {
        **base,
        "spent_amount": spent,
        "remaining_amount": remaining,
        "percentage_used": round(percentage_used, 2),
        "budget_status": compute_budget_status(base["limit_amount"], spent),
    }


async def get_budgets_with_usage(
    db: AgnosticDatabase, user_id: str, month: Optional[int] = None, year: Optional[int] = None
) -> list[dict[str, Any]]:
    docs = await list_budgets_for_user(db, user_id, month, year)
    return [await get_budget_usage(db, user_id, doc) for doc in docs]
