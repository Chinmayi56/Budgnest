"""
schemas/report.py

Pydantic response schemas for STEP 6's reporting/analytics backend
foundation. These endpoints return clean, real-database-backed JSON
intended to power STEP 8's React charts/dashboard later — no chart
rendering or UI happens here.
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from schemas.bill import PaymentSummaryResponse
from schemas.budget import BudgetWithUsage
from schemas.money_given import MoneyGivenSummaryResponse


class MonthlyFinancialSummaryResponse(BaseModel):
    """Response for GET /api/reports/monthly-summary."""

    month: str  # "YYYY-MM"
    total_income: Decimal
    total_expenses: Decimal
    total_payments: Decimal
    money_given: Decimal
    money_returned: Decimal
    upcoming_payments: Decimal
    net_change: Decimal


class CategorySummaryItem(BaseModel):
    category: str
    amount: Decimal


class CategorySummaryResponse(BaseModel):
    """Response for GET /api/reports/category-summary."""

    month: str  # "YYYY-MM"
    categories: list[CategorySummaryItem]


class IncomeExpenseSummaryResponse(BaseModel):
    """Response for GET /api/reports/income-expense-summary."""

    month: str  # "YYYY-MM"
    total_income: Decimal
    total_expenses: Decimal
    net: Decimal


class BudgetSummaryResponse(BaseModel):
    """Response for GET /api/reports/budget-summary. Reuses the Step 4 budget engine."""

    month: int
    year: int
    budgets: list[BudgetWithUsage]


class MonthlyTrendPoint(BaseModel):
    month: str  # "YYYY-MM"
    total_income: Decimal
    total_expenses: Decimal


class MonthlyTrendResponse(BaseModel):
    """Response for GET /api/reports/monthly-trend."""

    points: list[MonthlyTrendPoint]


# Payment-summary and money-given-summary reuse the existing Step 4/5
# response shapes directly (see routes/reports.py) rather than
# duplicating a second schema for the exact same data.
__all__ = [
    "MonthlyFinancialSummaryResponse",
    "CategorySummaryResponse",
    "CategorySummaryItem",
    "IncomeExpenseSummaryResponse",
    "BudgetSummaryResponse",
    "MonthlyTrendResponse",
    "MonthlyTrendPoint",
    "PaymentSummaryResponse",
    "MoneyGivenSummaryResponse",
]
