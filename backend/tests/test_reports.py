"""
tests/test_reports.py

Automated tests for STEP 6's reporting/analytics backend foundation:
monthly financial summary, category summary, income-vs-expense,
budget-vs-actual, payment summary, money-given summary, monthly
trend, filtering, and user data isolation.

Run with (from backend/, virtual environment active):
    pytest -v
"""

import datetime

import pytest


async def _seed_month_data(client, headers, month: int, year: int):
    await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "transaction_type": "INCOME",
            "amount": 50000,
            "transaction_date": f"{year:04d}-{month:02d}-02",
            "category": "SALARY",
            "status": "COMPLETED",
        },
    )
    await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "transaction_type": "EXPENSE",
            "amount": 5000,
            "transaction_date": f"{year:04d}-{month:02d}-05",
            "category": "FOOD",
            "status": "COMPLETED",
        },
    )
    await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "transaction_type": "EXPENSE",
            "amount": 3000,
            "transaction_date": f"{year:04d}-{month:02d}-06",
            "category": "TRAVEL",
            "status": "COMPLETED",
        },
    )
    await client.post(
        "/api/money-given",
        headers=headers,
        json={
            "person_name": "Ravi",
            "amount": 2000,
            "given_date": f"{year:04d}-{month:02d}-07",
            "category": "FRIEND",
        },
    )


async def test_monthly_summary_keeps_values_separate(client, auth_headers):
    headers, _ = auth_headers
    today = datetime.date.today()
    await _seed_month_data(client, headers, today.month, today.year)

    response = await client.get("/api/reports/monthly-summary", headers=headers, params={"month": today.month, "year": today.year})
    assert response.status_code == 200
    body = response.json()
    assert body["total_income"] == "50000.00"
    assert body["total_expenses"] == "8000.00"
    assert body["money_given"] == "2000.00"
    assert body["money_returned"] == "0.00"
    # income - expenses - money_given + money_returned
    assert body["net_change"] == "40000.00"


async def test_monthly_summary_defaults_to_current_month(client, auth_headers):
    headers, _ = auth_headers
    response = await client.get("/api/reports/monthly-summary", headers=headers)
    assert response.status_code == 200
    today = datetime.date.today()
    assert response.json()["month"] == f"{today.year:04d}-{today.month:02d}"


async def test_category_summary(client, auth_headers):
    headers, _ = auth_headers
    today = datetime.date.today()
    await _seed_month_data(client, headers, today.month, today.year)

    response = await client.get("/api/reports/category-summary", headers=headers, params={"month": today.month, "year": today.year})
    assert response.status_code == 200
    categories = {c["category"]: c["amount"] for c in response.json()["categories"]}
    assert categories["FOOD"] == "5000.00"
    assert categories["TRAVEL"] == "3000.00"


async def test_income_expense_summary(client, auth_headers):
    headers, _ = auth_headers
    today = datetime.date.today()
    await _seed_month_data(client, headers, today.month, today.year)

    response = await client.get(
        "/api/reports/income-expense-summary", headers=headers, params={"month": today.month, "year": today.year}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_income"] == "50000.00"
    assert body["total_expenses"] == "8000.00"
    assert body["net"] == "42000.00"


async def test_budget_summary_reuses_step4_engine(client, auth_headers):
    headers, _ = auth_headers
    today = datetime.date.today()
    await client.post(
        "/api/budgets",
        headers=headers,
        json={"budget_type": "CATEGORY", "category": "FOOD", "limit_amount": 5000, "month": today.month, "year": today.year},
    )
    await _seed_month_data(client, headers, today.month, today.year)

    response = await client.get("/api/reports/budget-summary", headers=headers, params={"month": today.month, "year": today.year})
    assert response.status_code == 200
    budgets = response.json()["budgets"]
    food_budget = next(b for b in budgets if b["category"] == "FOOD")
    assert food_budget["spent_amount"] == "5000.00"
    assert food_budget["budget_status"] == "WARNING"


async def test_payment_summary_report_endpoint(client, auth_headers):
    headers, _ = auth_headers
    response = await client.get("/api/reports/payment-summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "upcoming_count" in body
    assert "overdue_amount" in body


async def test_money_given_summary_report_endpoint(client, auth_headers):
    headers, _ = auth_headers
    today = datetime.date.today()
    await _seed_month_data(client, headers, today.month, today.year)

    response = await client.get("/api/reports/money-given-summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_money_given"] == "2000.00"


async def test_monthly_trend_returns_real_data_oldest_first(client, auth_headers):
    headers, _ = auth_headers
    today = datetime.date.today()
    await _seed_month_data(client, headers, today.month, today.year)

    response = await client.get("/api/reports/monthly-trend", headers=headers, params={"months": 3})
    assert response.status_code == 200
    points = response.json()["points"]
    assert len(points) == 3
    assert points[-1]["month"] == f"{today.year:04d}-{today.month:02d}"
    assert points[-1]["total_income"] == "50000.00"
    # Earlier months with no seeded data are real zeros, not invented numbers.
    assert points[0]["total_income"] == "0.00"


async def test_reports_require_auth(client):
    response = await client.get("/api/reports/monthly-summary")
    assert response.status_code == 401


async def test_reports_user_data_isolation(client, auth_headers, second_auth_headers):
    headers, _ = auth_headers
    other_headers, _ = second_auth_headers
    today = datetime.date.today()

    await _seed_month_data(client, headers, today.month, today.year)

    other_summary = await client.get(
        "/api/reports/monthly-summary", headers=other_headers, params={"month": today.month, "year": today.year}
    )
    assert other_summary.json()["total_income"] == "0.00"

    other_category = await client.get(
        "/api/reports/category-summary", headers=other_headers, params={"month": today.month, "year": today.year}
    )
    assert other_category.json()["categories"] == []
