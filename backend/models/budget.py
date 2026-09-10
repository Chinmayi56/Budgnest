"""
models/budget.py

Domain-level definitions for BudgetNest's STEP 4 personal budgeting
feature: the "budgets" collection.

A budget is a planning limit a user sets for a given month — either
an OVERALL limit (total spending for the month) or a CATEGORY limit
(spending within one category, e.g. FOOD). Budgets never store or
duplicate financial totals themselves: "spent" amounts are always
computed live from the Step 3 transaction/summary engine
(services/financial_service.py) via services/budget_service.py, so
there is exactly one source of truth for financial math.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from utils.money import from_decimal128, to_decimal128

BUDGETS_COLLECTION = "budgets"


class BudgetType(str, Enum):
    OVERALL = "OVERALL"
    CATEGORY = "CATEGORY"


class BudgetStatus(str, Enum):
    """
    Computed (never stored) status of a budget based on how much of
    its limit has been spent so far this period.
    """

    ON_TRACK = "ON_TRACK"
    WARNING = "WARNING"
    EXCEEDED = "EXCEEDED"


# A budget is considered WARNING once spend reaches this fraction of
# its limit, and EXCEEDED once spend passes the limit entirely.
WARNING_THRESHOLD = Decimal("0.80")


def compute_budget_status(limit_amount: Decimal, spent_amount: Decimal) -> BudgetStatus:
    if limit_amount <= 0:
        return BudgetStatus.EXCEEDED if spent_amount > 0 else BudgetStatus.ON_TRACK
    ratio = spent_amount / limit_amount
    if ratio > 1:
        return BudgetStatus.EXCEEDED
    if ratio >= WARNING_THRESHOLD:
        return BudgetStatus.WARNING
    return BudgetStatus.ON_TRACK


def new_budget_document(
    user_id: str,
    budget_type: BudgetType,
    limit_amount: Decimal,
    month: int,
    year: int,
    category: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "budget_type": budget_type.value,
        "category": category.strip().upper() if category else None,
        "limit_amount": to_decimal128(limit_amount),
        "month": month,
        "year": year,
        "notes": notes.strip() if notes else None,
        "created_at": now,
        "updated_at": now,
    }


def budget_doc_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw MongoDB budget document (without computed usage fields)."""
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "budget_type": BudgetType(doc["budget_type"]),
        "category": doc.get("category"),
        "limit_amount": from_decimal128(doc["limit_amount"]),
        "month": doc["month"],
        "year": doc["year"],
        "notes": doc.get("notes"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }
