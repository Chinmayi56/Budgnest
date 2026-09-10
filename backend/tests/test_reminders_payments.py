"""
tests/test_reminders_payments.py

Automated tests for STEP 6 Reminders & Upcoming Payments: reminder
configuration, priority, computed due_status (UPCOMING/DUE/OVERDUE/
PAID/CANCELLED), overdue listing, payment summary, monthly upcoming
total, and that mark-as-paid still creates exactly one real
transaction with no double-counting.

Run with (from backend/, virtual environment active):
    pytest -v
"""

import datetime

import pytest


def _iso(days_offset: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=days_offset)).isoformat()


async def test_create_bill_with_reminder_and_priority(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={
            "name": "Internet Bill",
            "amount": 799,
            "category": "BILLS",
            "payment_method": "UPI",
            "due_date": _iso(10),
            "is_recurring": True,
            "frequency": "MONTHLY",
            "priority": "HIGH",
            "reminder_enabled": True,
            "reminder_date": _iso(8),
            "notes": "Home internet",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["priority"] == "HIGH"
    assert body["reminder_enabled"] is True
    assert body["reminder_date"] == _iso(8)
    assert body["due_status"] == "UPCOMING"


async def test_reminder_date_after_due_date_rejected(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={
            "name": "Bad reminder",
            "amount": 100,
            "due_date": _iso(5),
            "is_recurring": False,
            "reminder_enabled": True,
            "reminder_date": _iso(10),
        },
    )
    assert response.status_code == 422


async def test_reminder_enabled_requires_reminder_date(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Bad reminder 2", "amount": 100, "due_date": _iso(5), "is_recurring": False, "reminder_enabled": True},
    )
    assert response.status_code == 422


async def test_invalid_amount_rejected(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Zero amount", "amount": 0, "due_date": _iso(5), "is_recurring": False},
    )
    assert response.status_code == 422


async def test_invalid_recurrence_missing_frequency_rejected(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Rent", "amount": 10000, "due_date": _iso(5), "is_recurring": True},
    )
    assert response.status_code == 422


async def test_due_status_due_today(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Due Today", "amount": 500, "due_date": _iso(0), "is_recurring": False},
    )
    assert create.json()["due_status"] == "DUE"


async def test_due_status_overdue(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Old Bill", "amount": 500, "due_date": _iso(-3), "is_recurring": False},
    )
    bill_id = create.json()["id"]
    assert create.json()["due_status"] == "OVERDUE"

    overdue = await client.get("/api/bills/overdue", headers=headers)
    assert overdue.status_code == 200
    ids = [item["id"] for item in overdue.json()["items"]]
    assert bill_id in ids
    for item in overdue.json()["items"]:
        assert item["due_status"] == "OVERDUE"


async def test_overdue_excludes_future_bills(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Future Bill", "amount": 500, "due_date": _iso(10), "is_recurring": False},
    )
    overdue = await client.get("/api/bills/overdue", headers=headers)
    names = [item["name"] for item in overdue.json()["items"]]
    assert "Future Bill" not in names


async def test_pay_bill_sets_due_status_paid_and_creates_transaction_once(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "College Fee", "amount": 15000, "due_date": _iso(2), "is_recurring": False},
    )
    bill_id = create.json()["id"]

    pay = await client.post(f"/api/bills/{bill_id}/pay", headers=headers, json={"payment_date": _iso(0)})
    assert pay.status_code == 200
    body = pay.json()
    assert body["due_status"] == "PAID"
    assert body["last_transaction_id"] is not None

    # No double-counting: exactly one PAYMENT transaction, balance reduced exactly once.
    summary_before_second_pay = await client.get("/api/finance/summary", headers=headers)
    assert summary_before_second_pay.json()["total_payments"] == "15000.00"

    # Bill is COMPLETED now; paying again is rejected, so the balance can't be double-deducted.
    second_pay = await client.post(f"/api/bills/{bill_id}/pay", headers=headers, json={})
    assert second_pay.status_code == 409
    summary_after = await client.get("/api/finance/summary", headers=headers)
    assert summary_after.json()["total_payments"] == "15000.00"


async def test_recurring_payment_next_occurrence_is_upcoming(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Rent", "amount": 10000, "due_date": _iso(0), "is_recurring": True, "frequency": "MONTHLY"},
    )
    bill_id = create.json()["id"]

    pay = await client.post(f"/api/bills/{bill_id}/pay", headers=headers, json={"payment_date": _iso(0)})
    body = pay.json()
    assert body["status"] == "ACTIVE"
    assert body["due_status"] == "UPCOMING"
    assert body["due_date"] != _iso(0)  # advanced to next month


async def test_update_bill_reminder_fields(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Netflix", "amount": 649, "due_date": _iso(15), "is_recurring": True, "frequency": "MONTHLY"},
    )
    bill_id = create.json()["id"]

    update = await client.patch(
        f"/api/bills/{bill_id}",
        headers=headers,
        json={"reminder_enabled": True, "reminder_date": _iso(13), "priority": "LOW", "description": "Streaming"},
    )
    assert update.status_code == 200
    body = update.json()
    assert body["reminder_enabled"] is True
    assert body["reminder_date"] == _iso(13)
    assert body["priority"] == "LOW"
    assert body["description"] == "Streaming"


async def test_cancel_bill_due_status_cancelled(client, auth_headers):
    headers, _ = auth_headers
    create = await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Subscription", "amount": 500, "due_date": _iso(5), "is_recurring": False},
    )
    bill_id = create.json()["id"]

    cancel = await client.delete(f"/api/bills/{bill_id}", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["due_status"] == "CANCELLED"


async def test_payment_summary_reflects_real_data(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/bills", headers=headers, json={"name": "Upcoming A", "amount": 1000, "due_date": _iso(5), "is_recurring": False}
    )
    overdue_create = await client.post(
        "/api/bills", headers=headers, json={"name": "Overdue A", "amount": 250, "due_date": _iso(-2), "is_recurring": False}
    )
    paid_create = await client.post(
        "/api/bills", headers=headers, json={"name": "Paid A", "amount": 300, "due_date": _iso(0), "is_recurring": False}
    )
    await client.post(f"/api/bills/{paid_create.json()['id']}/pay", headers=headers, json={})

    summary = await client.get("/api/bills/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["upcoming_count"] >= 1
    assert body["overdue_count"] >= 1
    assert body["overdue_amount"] == "250.00"
    assert body["paid_count"] >= 1

    # The same shape is available under /api/reports/payment-summary.
    reports_summary = await client.get("/api/reports/payment-summary", headers=headers)
    assert reports_summary.status_code == 200
    assert reports_summary.json()["paid_count"] == body["paid_count"]


async def test_monthly_upcoming_total(client, auth_headers):
    headers, _ = auth_headers
    today = datetime.date.today()
    same_month_due = today.replace(day=min(today.day + 1, 28)).isoformat() if today.day < 28 else today.isoformat()

    await client.post(
        "/api/bills",
        headers=headers,
        json={"name": "Rent", "amount": 10000, "due_date": same_month_due, "is_recurring": False},
    )

    response = await client.get(
        "/api/bills/monthly-upcoming", headers=headers, params={"month": today.month, "year": today.year}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["month"] == today.month
    assert body["year"] == today.year
    names = [item["name"] for item in body["items"]]
    assert "Rent" in names
    assert float(body["total"]) >= 10000.0


async def test_bills_summary_requires_auth(client):
    response = await client.get("/api/bills/summary")
    assert response.status_code == 401


async def test_reminder_payment_user_data_isolation(client, auth_headers, second_auth_headers):
    headers, _ = auth_headers
    other_headers, _ = second_auth_headers

    create = await client.post(
        "/api/bills",
        headers=headers,
        json={
            "name": "Rent",
            "amount": 10000,
            "due_date": _iso(-1),
            "is_recurring": False,
            "reminder_enabled": True,
            "reminder_date": _iso(-3),
        },
    )
    bill_id = create.json()["id"]

    # Other user's overdue/summary/monthly-upcoming must never include this bill.
    other_overdue = await client.get("/api/bills/overdue", headers=other_headers)
    assert all(item["id"] != bill_id for item in other_overdue.json()["items"])

    other_summary = await client.get("/api/bills/summary", headers=other_headers)
    assert other_summary.json()["overdue_count"] == 0

    other_get = await client.get(f"/api/bills/{bill_id}", headers=other_headers)
    assert other_get.status_code == 404
