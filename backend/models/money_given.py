"""
models/money_given.py

Domain-level definitions for BudgetNest's STEP 5 "Money Given &
Money Returned" feature: the "money_given" and "money_returns"
collections.

A MoneyGiven record tracks a personal money-lending relationship —
money one individual user gave to another person (a friend, family
member, etc.) and the return(s) received back over time. It is a
*relationship/tracking* record, not a second balance ledger: the
actual effect on the user's balance is always recorded through the
existing Step 3 transaction engine (models/transaction.py,
services/financial_service.py) via TransactionType.MONEY_GIVEN and
TransactionType.MONEY_RETURNED, exactly one real transaction per
financial event:

    - Creating a money-given record creates exactly one COMPLETED
      MONEY_GIVEN transaction, whose id is stored as
      `given_transaction_id`.
    - Recording a return creates exactly one COMPLETED
      MONEY_RETURNED transaction, whose id is stored on the
      corresponding money_returns document as `return_transaction_id`.

This one-to-one linkage is what prevents double-counting (spec
section 17): each money_given/money_returns document always
corresponds to exactly one Step 3 transaction, never zero and never
two.

BudgetNest is a personal finance application — this module
deliberately has no employee/company/accounting concept anywhere in
it (no OWNER/ACCOUNTANT/EMPLOYEE role, no payroll). "Person" here
always means an informal individual the user personally lent money
to (a friend, relative, colleague, etc.), never an employee.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from utils.money import from_decimal128, quantize_amount, to_decimal128

MONEY_GIVEN_COLLECTION = "money_given"
MONEY_RETURNS_COLLECTION = "money_returns"

ZERO = Decimal("0.00")


class MoneyGivenStatus(str, Enum):
    OUTSTANDING = "OUTSTANDING"
    PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"


class MoneyGivenCategory(str, Enum):
    """
    Personal money-lending categories/reasons. Deliberately excludes
    business/accounting categories (invoice, vendor payment, payroll,
    etc.) — see module docstring.
    """

    LOAN = "LOAN"
    FAMILY = "FAMILY"
    FRIEND = "FRIEND"
    EMERGENCY = "EMERGENCY"
    PERSONAL = "PERSONAL"
    OTHER = "OTHER"


def status_for_amounts(amount_given: Decimal, amount_returned: Decimal) -> MoneyGivenStatus:
    """Derive OUTSTANDING/PARTIALLY_RETURNED/SETTLED from the running totals (never returns CANCELLED — that is only ever set explicitly)."""
    if amount_returned <= ZERO:
        return MoneyGivenStatus.OUTSTANDING
    if amount_returned >= amount_given:
        return MoneyGivenStatus.SETTLED
    return MoneyGivenStatus.PARTIALLY_RETURNED


def new_money_given_document(
    user_id: str,
    person_name: str,
    amount_given: Decimal,
    given_date: date,
    given_transaction_id: str,
    reason: Optional[str] = None,
    category: Optional[MoneyGivenCategory] = None,
    payment_method: Optional[str] = None,
    expected_return_date: Optional[date] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Build the raw MongoDB document for a new money-given record. Initial returned amount is always zero (spec section 4)."""
    now = datetime.now(timezone.utc)
    amount_given = quantize_amount(amount_given)
    return {
        "user_id": user_id,
        "person_name": person_name.strip(),
        "amount_given": to_decimal128(amount_given),
        "amount_returned": to_decimal128(ZERO),
        "outstanding_amount": to_decimal128(amount_given),
        "reason": reason.strip() if reason else None,
        "category": category.value if category else None,
        "payment_method": payment_method,
        "given_date": given_date.isoformat(),
        "expected_return_date": expected_return_date.isoformat() if expected_return_date else None,
        "status": MoneyGivenStatus.OUTSTANDING.value,
        "notes": notes.strip() if notes else None,
        "given_transaction_id": given_transaction_id,
        "created_at": now,
        "updated_at": now,
    }


def money_given_doc_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "person_name": doc["person_name"],
        "amount_given": from_decimal128(doc["amount_given"]),
        "amount_returned": from_decimal128(doc["amount_returned"]),
        "outstanding_amount": from_decimal128(doc["outstanding_amount"]),
        "reason": doc.get("reason"),
        "category": MoneyGivenCategory(doc["category"]) if doc.get("category") else None,
        "payment_method": doc.get("payment_method"),
        "given_date": doc["given_date"],
        "expected_return_date": doc.get("expected_return_date"),
        "status": MoneyGivenStatus(doc["status"]),
        "notes": doc.get("notes"),
        "given_transaction_id": doc.get("given_transaction_id"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


def new_money_return_document(
    money_given_id: str,
    user_id: str,
    amount: Decimal,
    return_date: date,
    return_transaction_id: str,
    payment_method: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "money_given_id": money_given_id,
        "user_id": user_id,
        "amount": to_decimal128(quantize_amount(amount)),
        "return_date": return_date.isoformat(),
        "payment_method": payment_method,
        "notes": notes.strip() if notes else None,
        "return_transaction_id": return_transaction_id,
        "created_at": now,
        "updated_at": now,
    }


def money_return_doc_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "money_given_id": doc["money_given_id"],
        "user_id": doc["user_id"],
        "amount": from_decimal128(doc["amount"]),
        "return_date": doc["return_date"],
        "payment_method": doc.get("payment_method"),
        "notes": doc.get("notes"),
        "return_transaction_id": doc.get("return_transaction_id"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }
