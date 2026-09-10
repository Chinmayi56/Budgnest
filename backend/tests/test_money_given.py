"""
tests/test_money_given.py

Automated tests for STEP 5 "Money Given & Money Returned": creating
money-given records, full/partial/multiple returns, outstanding and
status calculation, listing/filtering, single-record retrieval with
return history, metadata updates, cancellation, summaries,
person-wise summaries, Step 3 balance integration, no-double-counting,
and user data isolation.

Run with (from backend/, virtual environment active):
    pytest -v
"""

import pytest


# ---------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------


async def test_create_money_given(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={
            "person_name": "Rahul",
            "amount": 5000,
            "reason": "Personal loan",
            "category": "LOAN",
            "payment_method": "UPI",
            "given_date": "2026-09-01",
            "expected_return_date": "2026-09-15",
            "notes": "Temporary personal loan",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["person_name"] == "Rahul"
    assert body["amount_given"] == "5000.00"
    assert body["amount_returned"] == "0.00"
    assert body["outstanding_amount"] == "5000.00"
    assert body["status"] == "OUTSTANDING"
    assert body["given_transaction_id"] is not None


async def test_create_money_given_invalid_amount(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={"person_name": "Rahul", "amount": 0, "given_date": "2026-09-01"},
    )
    assert response.status_code == 422


async def test_create_money_given_negative_amount(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={"person_name": "Rahul", "amount": -100, "given_date": "2026-09-01"},
    )
    assert response.status_code == 422


async def test_create_money_given_missing_person_name(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={"amount": 5000, "given_date": "2026-09-01"},
    )
    assert response.status_code == 422


async def test_create_money_given_invalid_expected_return_date(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={
            "person_name": "Rahul",
            "amount": 5000,
            "given_date": "2026-09-15",
            "expected_return_date": "2026-09-01",
        },
    )
    assert response.status_code == 422


async def test_create_money_given_requires_auth(client):
    response = await client.post(
        "/api/money-given",
        json={"person_name": "Rahul", "amount": 5000, "given_date": "2026-09-01"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------
# Returns — full, partial, multiple
# ---------------------------------------------------------------------


async def _create_money_given(client, headers, amount=5000, person_name="Rahul"):
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={"person_name": person_name, "amount": amount, "given_date": "2026-09-01"},
    )
    return response.json()["id"]


async def test_full_return_settles_record(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)

    response = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 5000, "return_date": "2026-09-10", "payment_method": "UPI"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount_returned"] == "5000.00"
    assert body["outstanding_amount"] == "0.00"
    assert body["status"] == "SETTLED"


async def test_partial_return_updates_status(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)

    response = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 2000, "return_date": "2026-09-05", "payment_method": "UPI"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount_returned"] == "2000.00"
    assert body["outstanding_amount"] == "3000.00"
    assert body["status"] == "PARTIALLY_RETURNED"


async def test_multiple_partial_returns_settle_over_time(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=10000)

    r1 = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 2000, "return_date": "2026-09-01", "payment_method": "UPI"},
    )
    assert r1.json()["status"] == "PARTIALLY_RETURNED"
    assert r1.json()["outstanding_amount"] == "8000.00"

    r2 = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 3000, "return_date": "2026-09-05", "payment_method": "CASH"},
    )
    assert r2.json()["status"] == "PARTIALLY_RETURNED"
    assert r2.json()["outstanding_amount"] == "5000.00"

    r3 = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 5000, "return_date": "2026-09-10", "payment_method": "BANK_TRANSFER"},
    )
    assert r3.json()["status"] == "SETTLED"
    assert r3.json()["outstanding_amount"] == "0.00"
    assert r3.json()["amount_returned"] == "10000.00"


async def test_return_amount_exceeding_outstanding_rejected(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)

    response = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 6000, "return_date": "2026-09-05"},
    )
    assert response.status_code == 422


async def test_zero_return_amount_rejected(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)

    response = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 0, "return_date": "2026-09-05"},
    )
    assert response.status_code == 422


async def test_return_after_settled_rejected(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)
    await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 5000, "return_date": "2026-09-05"},
    )

    response = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 100, "return_date": "2026-09-06"},
    )
    assert response.status_code == 409


async def test_return_against_unknown_record_returns_404(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given/64b7f9f9f9f9f9f9f9f9f9f9/return",
        headers=headers,
        json={"amount": 100, "return_date": "2026-09-06"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------
# Return history
# ---------------------------------------------------------------------


async def test_return_history_preserved_across_multiple_returns(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=10000)

    await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 2000, "return_date": "2026-09-01", "payment_method": "UPI"},
    )
    await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 3000, "return_date": "2026-09-05", "payment_method": "CASH"},
    )
    await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 5000, "return_date": "2026-09-10", "payment_method": "BANK_TRANSFER"},
    )

    response = await client.get(f"/api/money-given/{money_given_id}/returns", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 3
    assert [item["amount"] for item in items] == ["2000.00", "3000.00", "5000.00"]
    assert sum(float(item["amount"]) for item in items) == 10000.00

    # Also present on the single-record GET.
    single = await client.get(f"/api/money-given/{money_given_id}", headers=headers)
    assert len(single.json()["returns"]) == 3


# ---------------------------------------------------------------------
# List / filter / single retrieval
# ---------------------------------------------------------------------


async def test_list_money_given(client, auth_headers):
    headers, _ = auth_headers
    await _create_money_given(client, headers, amount=5000, person_name="Rahul")
    await _create_money_given(client, headers, amount=2000, person_name="Priya")

    response = await client.get("/api/money-given", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_filter_money_given_by_status(client, auth_headers):
    headers, _ = auth_headers
    settled_id = await _create_money_given(client, headers, amount=1000, person_name="Priya")
    await client.post(
        f"/api/money-given/{settled_id}/return",
        headers=headers,
        json={"amount": 1000, "return_date": "2026-09-05"},
    )
    await _create_money_given(client, headers, amount=5000, person_name="Rahul")

    response = await client.get("/api/money-given", headers=headers, params={"status": "OUTSTANDING"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["person_name"] == "Rahul"


async def test_filter_money_given_by_person_name(client, auth_headers):
    headers, _ = auth_headers
    await _create_money_given(client, headers, amount=5000, person_name="Rahul")
    await _create_money_given(client, headers, amount=2000, person_name="Priya")

    response = await client.get("/api/money-given", headers=headers, params={"person_name": "Priya"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["person_name"] == "Priya"


async def test_single_money_given_retrieval(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)

    response = await client.get(f"/api/money-given/{money_given_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == money_given_id


async def test_single_money_given_invalid_id_returns_404(client, auth_headers):
    headers, _ = auth_headers
    response = await client.get("/api/money-given/not-a-valid-object-id", headers=headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------
# Update metadata
# ---------------------------------------------------------------------


async def test_update_money_given_metadata(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)

    response = await client.patch(
        f"/api/money-given/{money_given_id}",
        headers=headers,
        json={"notes": "Updated notes", "expected_return_date": "2026-10-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["notes"] == "Updated notes"
    assert body["expected_return_date"] == "2026-10-01"
    # Financial fields untouched.
    assert body["amount_given"] == "5000.00"
    assert body["status"] == "OUTSTANDING"


async def test_update_money_given_unknown_returns_404(client, auth_headers):
    headers, _ = auth_headers
    response = await client.patch(
        "/api/money-given/64b7f9f9f9f9f9f9f9f9f9f9",
        headers=headers,
        json={"notes": "x"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------


async def test_cancel_money_given_reverses_balance_and_keeps_history(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)

    before = await client.get("/api/finance/summary", headers=headers)
    assert before.json()["total_money_given"] == "5000.00"
    assert before.json()["current_balance"] == "-5000.00"

    cancel = await client.delete(f"/api/money-given/{money_given_id}", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"

    # Still retrievable — history preserved.
    get_resp = await client.get(f"/api/money-given/{money_given_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "CANCELLED"

    # Balance effect reversed.
    after = await client.get("/api/finance/summary", headers=headers)
    assert after.json()["current_balance"] == "0.00"


async def test_cancel_already_cancelled_returns_409(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)
    await client.delete(f"/api/money-given/{money_given_id}", headers=headers)

    response = await client.delete(f"/api/money-given/{money_given_id}", headers=headers)
    assert response.status_code == 409


async def test_cancel_with_returns_reverses_all_transactions(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)
    await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 2000, "return_date": "2026-09-05"},
    )

    cancel = await client.delete(f"/api/money-given/{money_given_id}", headers=headers)
    assert cancel.status_code == 200

    summary = await client.get("/api/finance/summary", headers=headers)
    assert summary.json()["current_balance"] == "0.00"

    # Return history is still visible.
    returns = await client.get(f"/api/money-given/{money_given_id}/returns", headers=headers)
    assert len(returns.json()["items"]) == 1


# ---------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------


async def test_summary_calculation(client, auth_headers):
    headers, _ = auth_headers
    settled_id = await _create_money_given(client, headers, amount=2000, person_name="Priya")
    await client.post(
        f"/api/money-given/{settled_id}/return",
        headers=headers,
        json={"amount": 2000, "return_date": "2026-09-05"},
    )
    outstanding_id = await _create_money_given(client, headers, amount=5000, person_name="Rahul")
    await client.post(
        f"/api/money-given/{outstanding_id}/return",
        headers=headers,
        json={"amount": 1000, "return_date": "2026-09-05"},
    )

    response = await client.get("/api/money-given/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_money_given"] == "7000.00"
    assert body["total_money_returned"] == "3000.00"
    assert body["total_outstanding"] == "4000.00"
    assert body["active_records"] == 1
    assert body["settled_records"] == 1


async def test_summary_excludes_cancelled_records(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)
    await client.delete(f"/api/money-given/{money_given_id}", headers=headers)

    response = await client.get("/api/money-given/summary", headers=headers)
    body = response.json()
    assert body["total_money_given"] == "0.00"
    assert body["total_outstanding"] == "0.00"
    assert body["active_records"] == 0
    assert body["settled_records"] == 0


async def test_person_summary(client, auth_headers):
    headers, _ = auth_headers
    await _create_money_given(client, headers, amount=10000, person_name="Rahul")
    priya_id = await _create_money_given(client, headers, amount=5000, person_name="Priya")
    await client.post(
        f"/api/money-given/{priya_id}/return",
        headers=headers,
        json={"amount": 5000, "return_date": "2026-09-05"},
    )

    response = await client.get("/api/money-given/person-summary", headers=headers)
    assert response.status_code == 200
    people = {p["person_name"]: p for p in response.json()["people"]}
    assert people["Rahul"]["total_given"] == "10000.00"
    assert people["Rahul"]["outstanding"] == "10000.00"
    assert people["Priya"]["total_given"] == "5000.00"
    assert people["Priya"]["outstanding"] == "0.00"


async def test_total_outstanding_across_people(client, auth_headers):
    headers, _ = auth_headers
    rahul_id = await _create_money_given(client, headers, amount=10000, person_name="Rahul")
    await client.post(
        f"/api/money-given/{rahul_id}/return",
        headers=headers,
        json={"amount": 7000, "return_date": "2026-09-05"},
    )
    await _create_money_given(client, headers, amount=5000, person_name="Arjun")

    response = await client.get("/api/money-given/summary", headers=headers)
    body = response.json()
    assert body["total_outstanding"] == "8000.00"


# ---------------------------------------------------------------------
# Step 3 balance integration + no double-counting
# ---------------------------------------------------------------------


async def test_step3_balance_integration(client, auth_headers):
    headers, _ = auth_headers
    await client.post(
        "/api/finance/starting-balance",
        headers=headers,
        json={"amount": 50000, "date": "2026-08-01"},
    )

    money_given_id = await _create_money_given(client, headers, amount=5000)
    summary = await client.get("/api/finance/summary", headers=headers)
    assert summary.json()["current_balance"] == "45000.00"

    await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 2000, "return_date": "2026-09-05"},
    )
    summary = await client.get("/api/finance/summary", headers=headers)
    assert summary.json()["current_balance"] == "47000.00"

    await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 3000, "return_date": "2026-09-10"},
    )
    summary = await client.get("/api/finance/summary", headers=headers)
    assert summary.json()["current_balance"] == "50000.00"


async def test_no_double_counting_of_given_and_returned(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=5000)
    await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 2000, "return_date": "2026-09-05"},
    )

    summary = await client.get("/api/finance/summary", headers=headers)
    body = summary.json()
    # Exactly one MONEY_GIVEN transaction's worth and one MONEY_RETURNED
    # transaction's worth are reflected — not double the amounts.
    assert body["total_money_given"] == "5000.00"
    assert body["total_money_returned"] == "2000.00"

    transactions = await client.get(
        "/api/transactions", headers=headers, params={"transaction_type": "MONEY_GIVEN"}
    )
    assert transactions.json()["total"] == 1
    transactions = await client.get(
        "/api/transactions", headers=headers, params={"transaction_type": "MONEY_RETURNED"}
    )
    assert transactions.json()["total"] == 1


async def test_settled_record_has_zero_outstanding(client, auth_headers):
    headers, _ = auth_headers
    money_given_id = await _create_money_given(client, headers, amount=3000)
    response = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=headers,
        json={"amount": 3000, "return_date": "2026-09-05"},
    )
    assert response.json()["outstanding_amount"] == "0.00"
    assert response.json()["status"] == "SETTLED"


# ---------------------------------------------------------------------
# User data isolation
# ---------------------------------------------------------------------


async def test_money_given_user_data_isolation(client, auth_headers, second_auth_headers):
    headers, _ = auth_headers
    other_headers, _ = second_auth_headers

    money_given_id = await _create_money_given(client, headers, amount=5000, person_name="Rahul")

    # View
    assert (await client.get(f"/api/money-given/{money_given_id}", headers=other_headers)).status_code == 404
    # Return history
    assert (await client.get(f"/api/money-given/{money_given_id}/returns", headers=other_headers)).status_code == 404
    # Add a return
    return_resp = await client.post(
        f"/api/money-given/{money_given_id}/return",
        headers=other_headers,
        json={"amount": 100, "return_date": "2026-09-05"},
    )
    assert return_resp.status_code == 404
    # Update
    assert (
        await client.patch(f"/api/money-given/{money_given_id}", headers=other_headers, json={"notes": "x"})
    ).status_code == 404
    # Cancel
    assert (await client.delete(f"/api/money-given/{money_given_id}", headers=other_headers)).status_code == 404

    # Not included in the other user's list, summary, or person-summary.
    other_list = await client.get("/api/money-given", headers=other_headers)
    assert all(item["id"] != money_given_id for item in other_list.json()["items"])

    other_summary = await client.get("/api/money-given/summary", headers=other_headers)
    assert other_summary.json()["total_money_given"] == "0.00"

    other_person_summary = await client.get("/api/money-given/person-summary", headers=other_headers)
    assert other_person_summary.json()["people"] == []


async def test_money_given_requires_auth_for_all_routes(client):
    assert (await client.get("/api/money-given")).status_code == 401
    assert (await client.get("/api/money-given/summary")).status_code == 401
    assert (await client.get("/api/money-given/person-summary")).status_code == 401


async def test_same_person_name_isolated_across_users(client, auth_headers, second_auth_headers):
    """Two different users can each have a person named 'Rahul' without collision."""
    headers, _ = auth_headers
    other_headers, _ = second_auth_headers

    await _create_money_given(client, headers, amount=5000, person_name="Rahul")
    await _create_money_given(client, other_headers, amount=9000, person_name="Rahul")

    my_summary = await client.get("/api/money-given/person-summary", headers=headers)
    other_summary = await client.get("/api/money-given/person-summary", headers=other_headers)

    my_rahul = next(p for p in my_summary.json()["people"] if p["person_name"] == "Rahul")
    other_rahul = next(p for p in other_summary.json()["people"] if p["person_name"] == "Rahul")
    assert my_rahul["total_given"] == "5000.00"
    assert other_rahul["total_given"] == "9000.00"


# ---------------------------------------------------------------------
# Category / payment method validation
# ---------------------------------------------------------------------


async def test_invalid_category_rejected(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={"person_name": "Rahul", "amount": 5000, "given_date": "2026-09-01", "category": "NOT_A_CATEGORY"},
    )
    assert response.status_code == 422


async def test_invalid_payment_method_rejected(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={"person_name": "Rahul", "amount": 5000, "given_date": "2026-09-01", "payment_method": "BITCOIN"},
    )
    assert response.status_code == 422


async def test_invalid_date_rejected(client, auth_headers):
    headers, _ = auth_headers
    response = await client.post(
        "/api/money-given",
        headers=headers,
        json={"person_name": "Rahul", "amount": 5000, "given_date": "not-a-date"},
    )
    assert response.status_code == 422
