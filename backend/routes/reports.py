"""
routes/reports.py

STEP 6 reporting/analytics backend-foundation endpoints:
    GET /api/reports/monthly-summary
    GET /api/reports/category-summary
    GET /api/reports/income-expense-summary
    GET /api/reports/budget-summary
    GET /api/reports/payment-summary
    GET /api/reports/money-given-summary
    GET /api/reports/monthly-trend

These exist to give STEP 8's future React charts/dashboard clean,
real-database-backed JSON to consume — no chart rendering or
dashboard UI happens here (see services/report_service.py for why
every number is computed by composing the existing Step 3/4/5/6
engines rather than a second, competing calculation layer).

Every route resolves the acting user from the validated JWT
(get_current_user) and scopes every underlying query to that user's
id — a user_id is never accepted from the client.
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from motor.core import AgnosticDatabase

from database import get_database
from schemas.bill import PaymentSummaryResponse
from schemas.budget import BudgetWithUsage
from schemas.money_given import MoneyGivenSummaryResponse
from schemas.report import (
    BudgetSummaryResponse,
    CategorySummaryResponse,
    IncomeExpenseSummaryResponse,
    MonthlyFinancialSummaryResponse,
    MonthlyTrendResponse,
)
from schemas.user import UserPublic
from services import bill_service, money_given_service, report_service
from utils.deps import get_current_user

logger = logging.getLogger("budgetnest.reports")

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


def _resolved_month_year(month: int | None, year: int | None) -> tuple[int, int]:
    today = date.today()
    return month or today.month, year or today.year


@router.get(
    "/monthly-summary",
    response_model=MonthlyFinancialSummaryResponse,
    summary="Monthly financial summary: income, expenses, money given/returned, upcoming payments, net change",
)
async def read_monthly_financial_summary(
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2000, le=2100),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    resolved_month, resolved_year = _resolved_month_year(month, year)
    result = await report_service.monthly_financial_summary(db, current_user.id, resolved_month, resolved_year)
    return MonthlyFinancialSummaryResponse(**result)


@router.get(
    "/category-summary",
    response_model=CategorySummaryResponse,
    summary="Category expense breakdown for a month",
)
async def read_category_summary(
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2000, le=2100),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    resolved_month, resolved_year = _resolved_month_year(month, year)
    result = await report_service.category_summary(db, current_user.id, resolved_month, resolved_year)
    return CategorySummaryResponse(**result)


@router.get(
    "/income-expense-summary",
    response_model=IncomeExpenseSummaryResponse,
    summary="Income vs. expense totals for a month",
)
async def read_income_expense_summary(
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2000, le=2100),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    resolved_month, resolved_year = _resolved_month_year(month, year)
    result = await report_service.income_expense_summary(db, current_user.id, resolved_month, resolved_year)
    return IncomeExpenseSummaryResponse(**result)


@router.get(
    "/budget-summary",
    response_model=BudgetSummaryResponse,
    summary="Budget vs. actual for a month (reuses the Step 4 budget engine)",
)
async def read_budget_summary(
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2000, le=2100),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    resolved_month, resolved_year = _resolved_month_year(month, year)
    result = await report_service.budget_summary(db, current_user.id, resolved_month, resolved_year)
    return BudgetSummaryResponse(month=result["month"], year=result["year"], budgets=[BudgetWithUsage(**b) for b in result["budgets"]])


@router.get(
    "/payment-summary",
    response_model=PaymentSummaryResponse,
    summary="Upcoming/due/overdue/paid bill counts and amounts (reuses the Step 6 bill engine)",
)
async def read_payment_summary(
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    result = await bill_service.get_payment_summary(db, current_user.id)
    return PaymentSummaryResponse(**result)


@router.get(
    "/money-given-summary",
    response_model=MoneyGivenSummaryResponse,
    summary="Money given/returned/outstanding totals (reuses the Step 5 engine)",
)
async def read_money_given_summary(
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    result = await money_given_service.get_summary(db, current_user.id)
    return MoneyGivenSummaryResponse(**result)


@router.get(
    "/monthly-trend",
    response_model=MonthlyTrendResponse,
    summary="Trailing N-month income/expense trend (real data, oldest first)",
)
async def read_monthly_trend(
    months: int = Query(default=6, ge=1, le=24),
    end_month: int = Query(default=None, ge=1, le=12),
    end_year: int = Query(default=None, ge=2000, le=2100),
    current_user: UserPublic = Depends(get_current_user),
    db: AgnosticDatabase = Depends(get_database),
):
    result = await report_service.monthly_trend(db, current_user.id, months=months, end_month=end_month, end_year=end_year)
    return MonthlyTrendResponse(**result)
