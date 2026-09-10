"""
services/report_service.py

STEP 6 reporting/analytics backend foundation.

This module is deliberately a thin composition layer: it never
recomputes balance/spend math itself. Every number here comes from
one of the existing engines:
    - services/financial_service.py  (Step 3 — transactions/balance)
    - services/budget_service.py     (Step 4 — budgets)
    - services/bill_service.py       (Step 4/6 — bills/upcoming payments)
    - services/money_given_service.py(Step 5 — money given/returned)

Its only job is to shape that data into the report responses STEP 8's
future charts/dashboard will consume, and — for monthly-trend — loop
that composition across several months.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from motor.core import AgnosticDatabase

from models.transaction import (
    TRANSACTIONS_COLLECTION,
    AdjustmentDirection,
    TransactionStatus,
    TransactionType,
    signed_effect,
)
from services import bill_service, budget_service, financial_service
from utils.money import from_decimal128, quantize_amount

ZERO = Decimal("0.00")


def _month_key(month: int, year: int) -> str:
    return f"{year:04d}-{month:02d}"


def _month_bounds(month: int, year: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


async def _net_change_for_period(db: AgnosticDatabase, user_id: str, start: date, end: date) -> Decimal:
    """
    The true signed effect on the user's balance from every COMPLETED
    transaction dated within [start, end] — i.e. this period's actual
    contribution to current_balance (spec section 21). Computed
    directly from the same transactions collection Step 3 owns,
    reusing its signed_effect() sign table rather than re-deriving it.
    """
    net = ZERO
    query = {
        "user_id": user_id,
        "status": TransactionStatus.COMPLETED.value,
        "transaction_date": {"$gte": start.isoformat(), "$lte": end.isoformat()},
    }
    cursor = db[TRANSACTIONS_COLLECTION].find(query)
    async for doc in cursor:
        tx_type = TransactionType(doc["transaction_type"])
        amount = from_decimal128(doc["amount"])
        direction = AdjustmentDirection(doc["adjustment_direction"]) if doc.get("adjustment_direction") else None
        net += signed_effect(tx_type, amount, direction)
    return quantize_amount(net)


async def monthly_financial_summary(db: AgnosticDatabase, user_id: str, month: int, year: int) -> dict[str, Any]:
    """
    Spec section 21. Keeps actual expenses, money given, money
    returned, and upcoming (not-yet-paid) payments logically separate
    — upcoming_payments is informational only and is NOT part of
    net_change, matching Step 3/6's rule that scheduled bills never
    prematurely affect the balance (spec section 17).
    """
    monthly = await financial_service.calculate_monthly_summary(db, user_id, month, year)
    upcoming = await bill_service.get_monthly_upcoming_total(db, user_id, month, year)
    start, end = _month_bounds(month, year)
    net_change = await _net_change_for_period(db, user_id, start, end)

    return {
        "month": _month_key(month, year),
        "total_income": monthly["total_income"],
        "total_expenses": monthly["total_expenses"],
        "total_payments": monthly["total_payments"],
        "money_given": monthly["total_money_given"],
        "money_returned": monthly["total_money_returned"],
        "upcoming_payments": upcoming["total"],
        "net_change": net_change,
    }


async def category_summary(db: AgnosticDatabase, user_id: str, month: int, year: int) -> dict[str, Any]:
    """Spec section 22. Reuses the category breakdown already computed by calculate_monthly_summary."""
    monthly = await financial_service.calculate_monthly_summary(db, user_id, month, year)
    categories = [
        {"category": category, "amount": amount} for category, amount in sorted(monthly["categories"].items())
    ]
    return {"month": _month_key(month, year), "categories": categories}


async def income_expense_summary(db: AgnosticDatabase, user_id: str, month: int, year: int) -> dict[str, Any]:
    monthly = await financial_service.calculate_monthly_summary(db, user_id, month, year)
    total_income = monthly["total_income"]
    total_expenses = monthly["total_expenses"]
    return {
        "month": _month_key(month, year),
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net": quantize_amount(total_income - total_expenses),
    }


async def budget_summary(db: AgnosticDatabase, user_id: str, month: int, year: int) -> dict[str, Any]:
    """Spec section 24. Reuses the Step 4 budget engine — no second budget calculation."""
    budgets = await budget_service.get_budgets_with_usage(db, user_id, month=month, year=year)
    return {"month": month, "year": year, "budgets": budgets}


async def monthly_trend(
    db: AgnosticDatabase, user_id: str, months: int = 6, end_month: Optional[int] = None, end_year: Optional[int] = None
) -> dict[str, Any]:
    """
    Spec section 23. Returns real per-month income/expense totals for
    the trailing `months` months (inclusive of the end month),
    oldest-first — never invented data.
    """
    today = date.today()
    end_month = end_month or today.month
    end_year = end_year or today.year

    points = []
    month, year = end_month, end_year
    collected = []
    for _ in range(months):
        collected.append((month, year))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    collected.reverse()

    for month_i, year_i in collected:
        monthly = await financial_service.calculate_monthly_summary(db, user_id, month_i, year_i)
        points.append(
            {
                "month": _month_key(month_i, year_i),
                "total_income": monthly["total_income"],
                "total_expenses": monthly["total_expenses"],
            }
        )

    return {"points": points}
