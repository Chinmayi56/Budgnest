"""
tests/test_bills.py

Automated tests for STEP 4 Payment/Bill scheduling: one-off and
recurring bills, marking bills paid (and that this creates a real
PAYMENT transaction through the Step 3 engine), upcoming-bills
filtering, and user data isolation.

Run with (from backend/, virtual environment active):
    pytest -v
"""

import pytest


async def test_create_one_off_bill(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Laptop EMI", "amount": 3000, "due_date": "2026-09-01", "is_recurring": False},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_recurring"] is False
    assert body["frequency"] is None
    assert body["status"] == "ACTIVE"


async def test_create_recurring_bill_requires_frequency(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Rent", "amount": 15000, "due_date": "2026-09-01", "is_recurring": True},
    )
    assert response.status_code == 422


async def test_one_off_bill_rejects_frequency(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={
            "name": "Laptop EMI",
            "amount": 3000,
            "due_date": "2026-09-01",
            "is_recurring": False,
            "frequency": "MONTHLY",
        },
    )
    assert response.status_code == 422


async def test_create_recurring_bill(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={
            "name": "Rent",
            "amount": 15000,
            "due_date": "2026-09-01",
            "is_recurring": True,
            "frequency": "MONTHLY",
            "category": "RENT",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_recurring"] is True
    assert body["frequency"] == "MONTHLY"


async def test_pay_one_off_bill_creates_transaction_and_completes(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Laptop EMI", "amount": 3000, "due_date": "2026-09-01", "is_recurring": False},
    )
    bill_id = create.json()["id"]

    pay = await client.post(f"/api/bills/{bill_id}/pay", headers=headers, json={"payment_date": "2026-09-01"})
    assert pay.status_code == 200
    body = pay.json()
    assert body["status"] == "COMPLETED"
    assert body["last_paid_date"] == "2026-09-01"
    assert body["last_transaction_id"] is not None

    # The payment must show up as a real transaction affecting the balance.
    tx = await client.get(f"/api/transactions/{body['last_transaction_id']}", headers=headers)
    assert tx.status_code == 200
    tx_body = tx.json()
    assert tx_body["transaction_type"] == "PAYMENT"
    assert tx_body["amount"] == "3000.00"
    assert tx_body["status"] == "COMPLETED"

    summary = await client.get("/api/finance/summary", headers=headers)
    assert summary.json()["total_payments"] == "3000.00"


async def test_pay_recurring_bill_advances_due_date_and_stays_active(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={
            "name": "Internet",
            "amount": 999,
            "due_date": "2026-08-05",
            "is_recurring": True,
            "frequency": "MONTHLY",
        },
    )
    bill_id = create.json()["id"]

    pay = await client.post(f"/api/bills/{bill_id}/pay", headers=headers, json={"payment_date": "2026-08-05"})
    assert pay.status_code == 200
    body = pay.json()
    assert body["status"] == "ACTIVE"
    assert body["due_date"] == "2026-09-05"


async def test_pay_inactive_bill_rejected(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Laptop EMI", "amount": 3000, "due_date": "2026-09-01", "is_recurring": False},
    )
    bill_id = create.json()["id"]
    await client.delete(f"/api/bills/{bill_id}", headers=headers)  # cancels it

    pay = await client.post(f"/api/bills/{bill_id}/pay", headers=headers, json={})
    assert pay.status_code == 409


async def test_cancel_bill_is_soft_delete(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Subscription", "amount": 500, "due_date": "2026-09-01", "is_recurring": False},
    )
    bill_id = create.json()["id"]

    cancel = await client.delete(f"/api/bills/{bill_id}", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"

    # Still retrievable (history preserved), just no longer active.
    get_resp = await client.get(f"/api/bills/{bill_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "CANCELLED"


async def test_upcoming_bills_filters_by_window_and_active_status(client, auth_headers):
    headers, _ = auth_headers
    import datetime

    soon = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
    far = (datetime.date.today() + datetime.timedelta(days=200)).isoformat()

    soon_bill = await client.post(
        "/api/bills", headers=headers, json={"name": "Soon Bill", "amount": 100, "due_date": soon, "is_recurring": False}
    )
    await client.post(
        "/api/bills", headers=headers, json={"name": "Far Bill", "amount": 100, "due_date": far, "is_recurring": False}
    )

    response = await client.get("/api/bills/upcoming", headers=headers, params={"days": 30})
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert "Soon Bill" in names
    assert "Far Bill" not in names
    assert soon_bill.json()["id"] in [item["id"] for item in response.json()["items"]]


async def test_bills_require_auth(client):
    response = await client.get("/api/bills")
    assert response.status_code == 401


async def test_bill_user_data_isolation(client, auth_headers, second_auth_headers):
    headers, _ = auth_headers
    other_headers, _ = second_auth_headers

    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Rent", "amount": 15000, "due_date": "2026-09-01", "is_recurring": False},
    )
    bill_id = create.json()["id"]

    assert (await client.get(f"/api/bills/{bill_id}", headers=other_headers)).status_code == 404
    pay_resp = await client.post(f"/api/bills/{bill_id}/pay", headers=other_headers, json={})
    assert pay_resp.status_code == 404

    other_list = await client.get("/api/bills", headers=other_headers)
    assert all(item["id"] != bill_id for item in other_list.json()["items"])
