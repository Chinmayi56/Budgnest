"""
tests/test_budgets.py

Automated tests for STEP 4 personal budgets (overall + per-category
monthly limits), including that usage is computed live from Step 3
transaction data and that budgets are isolated per user.

Run with (from backend/, virtual environment active):
    pytest -v
"""

import pytest


async def _add_expense(client, headers, amount, category, day=15, status="COMPLETED"):
    return await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "transaction_type": "EXPENSE",
            "amount": amount,
            "category": category,
            "transaction_date": f"2026-08-{day:02d}",
            "status": status,
        },
    )


async def test_create_overall_budget(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/budgets",
        headers=headers,
        json={"budget_type": "OVERALL", "limit_amount": 20000, "month": 8, "year": 2026},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["budget_type"] == "OVERALL"
    assert body["category"] is None
    assert body["limit_amount"] == "20000.00"
    assert body["spent_amount"] == "0.00"
    assert body["budget_status"] == "ON_TRACK"


async def test_create_category_budget(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/budgets",
        headers=headers,
        json={"budget_type": "CATEGORY", "category": "food", "limit_amount": 5000, "month": 8, "year": 2026},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["budget_type"] == "CATEGORY"
    assert body["category"] == "FOOD"


async def test_category_budget_requires_category(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/budgets",
        headers=headers,
        json={"budget_type": "CATEGORY", "limit_amount": 5000, "month": 8, "year": 2026},
    )
    assert response.status_code == 422


async def test_overall_budget_rejects_category(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/budgets",
        headers=headers,
        json={"budget_type": "OVERALL", "category": "FOOD", "limit_amount": 5000, "month": 8, "year": 2026},
    )
    assert response.status_code == 422


async def test_duplicate_budget_rejected(client, auth_headers):
    headers, _ = auth_headers
    payload = {"budget_type": "OVERALL", "limit_amount": 20000, "month": 8, "year": 2026}
    first = await client.post("/api/budgets", headers=headers, json=payload)
    assert first.status_code == 201
    second = await client.post("/api/budgets", headers=headers, json=payload)
    assert second.status_code == 409


async def test_overall_budget_usage_reflects_completed_expenses_only(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/budgets", headers=headers, json={"budget_type": "OVERALL", "limit_amount": 10000, "month": 8, "year": 2026}
    )
    await _add_expense(client, headers, 3000, "FOOD")
    await _add_expense(client, headers, 1000, "TRAVEL")
    # Pending and cancelled expenses must NOT count toward spend.
    await _add_expense(client, headers, 5000, "SHOPPING", status="PENDING")
    await _add_expense(client, headers, 9999, "OTHER", status="CANCELLED")

    response = await client.get("/api/budgets", headers=headers, params={"month": 8, "year": 2026})
    assert response.status_code == 200
    items = response.json()["items"]
    overall = next(item for item in items if item["budget_type"] == "OVERALL")
    assert overall["spent_amount"] == "4000.00"
    assert overall["remaining_amount"] == "6000.00"
    assert overall["budget_status"] == "ON_TRACK"


async def test_category_budget_usage_isolated_by_category(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/budgets",
        headers=headers,
        json={"budget_type": "CATEGORY", "category": "FOOD", "limit_amount": 2000, "month": 8, "year": 2026},
    )
    await _add_expense(client, headers, 1000, "FOOD")
    await _add_expense(client, headers, 5000, "TRAVEL")  # different category, must not count

    response = await client.get("/api/budgets", headers=headers, params={"month": 8, "year": 2026})
    items = response.json()["items"]
    food_budget = next(item for item in items if item["budget_type"] == "CATEGORY")
    assert food_budget["spent_amount"] == "1000.00"


async def test_budget_status_warning_and_exceeded(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/budgets",
        headers=headers,
        json={"budget_type": "CATEGORY", "category": "FOOD", "limit_amount": 1000, "month": 8, "year": 2026},
    )
    await _add_expense(client, headers, 850, "FOOD")  # 85% -> WARNING
    response = await client.get("/api/budgets", headers=headers, params={"month": 8, "year": 2026})
    body = response.json()["items"][0]
    assert body["budget_status"] == "WARNING"

    await _add_expense(client, headers, 500, "FOOD")  # now 135% -> EXCEEDED
    response = await client.get("/api/budgets", headers=headers, params={"month": 8, "year": 2026})
    body = response.json()["items"][0]
    assert body["budget_status"] == "EXCEEDED"


async def test_update_budget_limit(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/budgets", headers=headers, json={"budget_type": "OVERALL", "limit_amount": 10000, "month": 8, "year": 2026}
    )
    budget_id = create.json()["id"]
    response = await client.patch(f"/api/budgets/{budget_id}", headers=headers, json={"limit_amount": 15000})
    assert response.status_code == 200
    assert response.json()["limit_amount"] == "15000.00"


async def test_delete_budget(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/budgets", headers=headers, json={"budget_type": "OVERALL", "limit_amount": 10000, "month": 8, "year": 2026}
    )
    budget_id = create.json()["id"]
    response = await client.delete(f"/api/budgets/{budget_id}", headers=headers)
    assert response.status_code == 204
    get_response = await client.get(f"/api/budgets/{budget_id}", headers=headers)
    assert get_response.status_code == 404


async def test_budget_requires_auth(client):
    response = await client.get("/api/budgets")
    assert response.status_code == 401


async def test_budget_user_data_isolation(client, auth_headers, second_auth_headers):
    headers, _ = auth_headers
    other_headers, _ = second_auth_headers

    create = await client.post(
        "/api/budgets", headers=headers, json={"budget_type": "OVERALL", "limit_amount": 10000, "month": 8, "year": 2026}
    )
    budget_id = create.json()["id"]

    # Other user cannot read, update, or delete this budget.
    assert (await client.get(f"/api/budgets/{budget_id}", headers=other_headers)).status_code == 404
    patch_resp = await client.patch(f"/api/budgets/{budget_id}", headers=other_headers, json={"limit_amount": 1})
    assert patch_resp.status_code == 404
    assert (await client.delete(f"/api/budgets/{budget_id}", headers=other_headers)).status_code == 404

    # Other user's budget list must not include this budget.
    other_list = await client.get("/api/budgets", headers=other_headers, params={"month": 8, "year": 2026})
    assert all(item["id"] != budget_id for item in other_list.json()["items"])
