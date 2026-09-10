"""
tests/test_finance.py

Automated tests for the Step 3 core personal financial engine:
starting balance, transactions (all types/statuses), balance
calculation, filtering, daily/monthly summaries, user data isolation,
and validation.

Run with (from backend/, virtual environment active):
    pytest -v
"""

import pytest


# ---------------------------------------------------------------------
# Starting balance
# ---------------------------------------------------------------------


async def test_create_starting_balance(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/finance/starting-balance",
        headers=headers,
        json={"amount": 50000, "date": "2026-08-01", "notes": "Initial personal balance"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == "50000.00"
    assert body["date"] == "2026-08-01"


async def test_create_starting_balance_requires_auth(client):
    response = await client.post(
        "/api/finance/starting-balance", json={"amount": 50000, "date": "2026-08-01"}
    )
    assert response.status_code == 401


async def test_create_starting_balance_invalid_amount(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/finance/starting-balance", headers=headers, json={"amount": 0, "date": "2026-08-01"}
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/finance/starting-balance", headers=headers, json={"amount": -100, "date": "2026-08-01"}
    )
    assert response.status_code == 422


async def test_duplicate_starting_balance_rejected(client, auth_headers):
    headers, _ = auth_headers
    first = await client.post(
        "/api/finance/starting-balance", headers=headers, json={"amount": 50000, "date": "2026-08-01"}
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/finance/starting-balance", headers=headers, json={"amount": 60000, "date": "2026-08-02"}
    )
    assert second.status_code == 409


async def test_adjust_starting_balance(client, auth_headers):
    headers, _ = auth_headers
    await client.post("/api/finance/starting-balance", headers=headers, json={"amount": 50000, "date": "2026-08-01"})

    response = await client.patch("/api/finance/starting-balance", headers=headers, json={"amount": 55000})
    assert response.status_code == 200
    assert response.json()["amount"] == "55000.00"


# ---------------------------------------------------------------------
# Transaction creation by type
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"transaction_type": "INCOME", "amount": 25000, "category": "SALARY", "transaction_date": "2026-08-05"},
        {"transaction_type": "EXPENSE", "amount": 300, "category": "FOOD", "transaction_date": "2026-08-05"},
        {"transaction_type": "PAYMENT", "amount": 5000, "category": "BILLS", "transaction_date": "2026-08-05"},
        {"transaction_type": "MONEY_GIVEN", "amount": 5000, "person_name": "Ravi", "transaction_date": "2026-08-05"},
        {"transaction_type": "MONEY_RETURNED", "amount": 2000, "person_name": "Ravi", "transaction_date": "2026-08-05"},
        {"transaction_type": "REFUND", "amount": 500, "category": "SHOPPING", "transaction_date": "2026-08-05"},
    ],
)
async def test_create_transaction_each_type(client, auth_headers, payload):
    headers, _ = auth_headers
    response = await client.post("/api/transactions", headers=headers, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["transaction_type"] == payload["transaction_type"]
    assert body["status"] == "COMPLETED"


async def test_create_adjustment_transaction_requires_direction(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "ADJUSTMENT", "amount": 100, "transaction_date": "2026-08-05"},
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "transaction_type": "ADJUSTMENT",
            "amount": 100,
            "adjustment_direction": "INCREASE",
            "transaction_date": "2026-08-05",
        },
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------
# Balance calculation
# ---------------------------------------------------------------------


async def test_current_balance_matches_spec_example(client, auth_headers):
    """Reproduces the example in the Step 3 spec: 50000 + 25000 - 8000 - 5000 - 5000 + 2000 = 59000."""
    headers, _ = auth_headers
    await client.post("/api/finance/starting-balance", headers=headers, json={"amount": 50000, "date": "2026-08-01"})

    txs = [
        {"transaction_type": "INCOME", "amount": 25000, "transaction_date": "2026-08-05"},
        {"transaction_type": "EXPENSE", "amount": 8000, "transaction_date": "2026-08-05"},
        {"transaction_type": "PAYMENT", "amount": 5000, "transaction_date": "2026-08-05"},
        {"transaction_type": "MONEY_GIVEN", "amount": 5000, "transaction_date": "2026-08-05"},
        {"transaction_type": "MONEY_RETURNED", "amount": 2000, "transaction_date": "2026-08-05"},
    ]
    for tx in txs:
        resp = await client.post("/api/transactions", headers=headers, json=tx)
        assert resp.status_code == 201

    summary = await client.get("/api/finance/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["current_balance"] == "59000.00"
    assert body["total_income"] == "25000.00"
    assert body["total_expenses"] == "8000.00"


async def test_pending_transaction_does_not_affect_current_balance(client, auth_headers):
    headers, _ = auth_headers
    await client.post("/api/finance/starting-balance", headers=headers, json={"amount": 10000, "date": "2026-08-01"})

    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 3000, "status": "PENDING", "transaction_date": "2026-08-05"},
    )

    summary = await client.get("/api/finance/summary", headers=headers)
    body = summary.json()
    assert body["current_balance"] == "10000.00"
    assert body["pending_commitments"] == "3000.00"
    assert body["available_balance"] == "7000.00"


async def test_cancelled_transaction_does_not_affect_balance(client, auth_headers):
    headers, _ = auth_headers
    await client.post("/api/finance/starting-balance", headers=headers, json={"amount": 10000, "date": "2026-08-01"})

    create_resp = await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 3000, "transaction_date": "2026-08-05"},
    )
    tx_id = create_resp.json()["id"]

    summary_before = await client.get("/api/finance/summary", headers=headers)
    assert summary_before.json()["current_balance"] == "7000.00"

    cancel_resp = await client.delete(f"/api/transactions/{tx_id}", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    summary_after = await client.get("/api/finance/summary", headers=headers)
    assert summary_after.json()["current_balance"] == "10000.00"


async def test_adjustment_increase_and_decrease(client, auth_headers):
    headers, _ = auth_headers
    await client.post("/api/finance/starting-balance", headers=headers, json={"amount": 1000, "date": "2026-08-01"})

    await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "transaction_type": "ADJUSTMENT",
            "amount": 200,
            "adjustment_direction": "INCREASE",
            "transaction_date": "2026-08-05",
        },
    )
    summary = await client.get("/api/finance/summary", headers=headers)
    assert summary.json()["current_balance"] == "1200.00"

    await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "transaction_type": "ADJUSTMENT",
            "amount": 500,
            "adjustment_direction": "DECREASE",
            "transaction_date": "2026-08-05",
        },
    )
    summary2 = await client.get("/api/finance/summary", headers=headers)
    assert summary2.json()["current_balance"] == "700.00"


# ---------------------------------------------------------------------
# Transaction listing / filtering / retrieval / update
# ---------------------------------------------------------------------


async def test_list_transactions(client, auth_headers):
    headers, _ = auth_headers
    for i in range(3):
        await client.post(
            "/api/transactions",
            headers=headers,
            json={"transaction_type": "EXPENSE", "amount": 100 + i, "transaction_date": "2026-08-05"},
        )

    response = await client.get("/api/transactions", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


async def test_filter_transactions_by_type_and_date(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 100, "transaction_date": "2026-08-01"},
    )
    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "INCOME", "amount": 500, "transaction_date": "2026-08-10"},
    )

    response = await client.get("/api/transactions?transaction_type=INCOME", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["transaction_type"] == "INCOME"

    response = await client.get(
        "/api/transactions?start_date=2026-08-05&end_date=2026-08-15", headers=headers
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["transaction_date"] == "2026-08-10"


async def test_get_single_transaction(client, auth_headers):
    headers, _ = auth_headers
    create_resp = await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 100, "transaction_date": "2026-08-05"},
    )
    tx_id = create_resp.json()["id"]

    response = await client.get(f"/api/transactions/{tx_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == tx_id


async def test_get_transaction_invalid_id(client, auth_headers):
    headers, _ = auth_headers
    response = await client.get("/api/transactions/not-a-valid-object-id", headers=headers)
    assert response.status_code == 404


async def test_update_transaction(client, auth_headers):
    headers, _ = auth_headers
    create_resp = await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 100, "category": "FOOD", "transaction_date": "2026-08-05"},
    )
    tx_id = create_resp.json()["id"]

    response = await client.patch(f"/api/transactions/{tx_id}", headers=headers, json={"amount": 150})
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "150.00"
    assert body["updated_at"] != body["created_at"]


# ---------------------------------------------------------------------
# Daily / monthly summaries
# ---------------------------------------------------------------------


async def test_daily_summary(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 300, "category": "FOOD", "transaction_date": "2026-08-25"},
    )
    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 150, "category": "TRAVEL", "transaction_date": "2026-08-25"},
    )
    # Different day — must not be included.
    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 999, "transaction_date": "2026-08-24"},
    )

    response = await client.get("/api/finance/daily-summary?date=2026-08-25", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_expenses"] == "450.00"
    assert body["transaction_count"] == 2
    assert body["categories"]["FOOD"] == "300.00"
    assert body["categories"]["TRAVEL"] == "150.00"


async def test_monthly_summary(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "INCOME", "amount": 25000, "transaction_date": "2026-08-03"},
    )
    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 15500, "transaction_date": "2026-08-20"},
    )
    # Different month — must not be included.
    await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 99999, "transaction_date": "2026-09-01"},
    )

    response = await client.get("/api/finance/monthly-summary?month=8&year=2026", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_income"] == "25000.00"
    assert body["total_expenses"] == "15500.00"


# ---------------------------------------------------------------------
# User data isolation & auth
# ---------------------------------------------------------------------


async def test_user_data_isolation_transactions(client, auth_headers, second_auth_headers):
    headers_a, _ = auth_headers
    headers_b, _ = second_auth_headers

    create_resp = await client.post(
        "/api/transactions",
        headers=headers_a,
        json={"transaction_type": "EXPENSE", "amount": 100, "transaction_date": "2026-08-05"},
    )
    tx_id = create_resp.json()["id"]

    # User B cannot read User A's transaction.
    response = await client.get(f"/api/transactions/{tx_id}", headers=headers_b)
    assert response.status_code == 404

    # User B cannot update or cancel it either.
    response = await client.patch(f"/api/transactions/{tx_id}", headers=headers_b, json={"amount": 1})
    assert response.status_code == 404
    response = await client.delete(f"/api/transactions/{tx_id}", headers=headers_b)
    assert response.status_code == 404

    # User B's transaction list is empty.
    listing = await client.get("/api/transactions", headers=headers_b)
    assert listing.json()["total"] == 0


async def test_user_data_isolation_balance_and_summary(client, auth_headers, second_auth_headers):
    headers_a, _ = auth_headers
    headers_b, _ = second_auth_headers

    await client.post("/api/finance/starting-balance", headers=headers_a, json={"amount": 50000, "date": "2026-08-01"})
    await client.post(
        "/api/transactions",
        headers=headers_a,
        json={"transaction_type": "INCOME", "amount": 1000, "transaction_date": "2026-08-05"},
    )

    # User B has their own, independent (empty) balance.
    response = await client.get("/api/finance/starting-balance", headers=headers_b)
    assert response.status_code == 404

    summary_b = await client.get("/api/finance/summary", headers=headers_b)
    assert summary_b.json()["current_balance"] == "0.00"

    summary_a = await client.get("/api/finance/summary", headers=headers_a)
    assert summary_a.json()["current_balance"] == "51000.00"


async def test_unauthorized_access_to_finance_endpoints(client):
    assert (await client.get("/api/finance/summary")).status_code == 401
    assert (await client.get("/api/transactions")).status_code == 401
    assert (
        await client.post("/api/transactions", json={"transaction_type": "EXPENSE", "amount": 1, "transaction_date": "2026-08-05"})
    ).status_code == 401


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


async def test_invalid_amount_rejected(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": -50, "transaction_date": "2026-08-05"},
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "EXPENSE", "amount": 0, "transaction_date": "2026-08-05"},
    )
    assert response.status_code == 422


async def test_invalid_transaction_type_rejected(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "SALARY", "amount": 100, "transaction_date": "2026-08-05"},
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/transactions",
        headers=headers,
        json={"transaction_type": "PAYROLL", "amount": 100, "transaction_date": "2026-08-05"},
    )
    assert response.status_code == 422


async def test_invalid_transaction_id_on_update(client, auth_headers):
    headers, _ = auth_headers
    response = await client.patch("/api/transactions/not-a-valid-id", headers=headers, json={"amount": 5})
    assert response.status_code == 404
