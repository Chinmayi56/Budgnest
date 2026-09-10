"""
models/transaction.py

Domain-level definitions for BudgetNest's core PERSONAL financial
engine: the "transactions" collection and the "starting_balances"
collection.

BudgetNest is a personal budget and expense management application
for a single individual managing their own money — NOT a company ERP.
There is deliberately no SALARY/EMPLOYEE_SALARY/PAYROLL transaction
type and no employee/company/accounting concept anywhere in this
module. A salary a user personally receives is simply an INCOME
transaction with category="SALARY" (a plain string category, not a
special type).
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from utils.money import from_decimal128, to_decimal128

TRANSACTIONS_COLLECTION = "transactions"
STARTING_BALANCES_COLLECTION = "starting_balances"


class TransactionType(str, Enum):
    """
    Personal financial transaction types.

    Deliberately excludes any employee/payroll/company concept
    (SALARY, EMPLOYEE_SALARY, PAYROLL, COMPANY_PAYMENT, etc.) — see
    module docstring.
    """

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    PAYMENT = "PAYMENT"
    MONEY_GIVEN = "MONEY_GIVEN"
    MONEY_RETURNED = "MONEY_RETURNED"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"


class TransactionStatus(str, Enum):
    """
    Transaction lifecycle status.

    Only COMPLETED transactions affect the actual balance. PENDING
    transactions represent upcoming/committed amounts (see
    financial_service.get_available_balance) and CANCELLED
    transactions never affect any balance calculation.
    """

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AdjustmentDirection(str, Enum):
    """
    Only meaningful when transaction_type == ADJUSTMENT.

    ADJUSTMENT amounts are always stored as a positive magnitude (like
    every other transaction type, keeping amount validation
    consistent); this field says which way the adjustment moves the
    balance.
    """

    INCREASE = "INCREASE"
    DECREASE = "DECREASE"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    OTHER = "OTHER"


# Suggested personal expense/income categories (section 17 of the spec).
# Categories are stored as plain, normalized strings rather than a
# locked enum so the set stays extensible without a schema change —
# this list is only a suggestion surfaced to clients, not an
# enforced whitelist.
SUGGESTED_CATEGORIES: list[str] = [
    "FOOD",
    "GROCERIES",
    "TRAVEL",
    "FUEL",
    "SHOPPING",
    "ENTERTAINMENT",
    "RENT",
    "ELECTRICITY",
    "INTERNET",
    "PHONE",
    "EDUCATION",
    "HEALTH",
    "SUBSCRIPTIONS",
    "BILLS",
    "SALARY",
    "OTHER",
]

# Types whose COMPLETED effect decreases the balance. Used both for
# the balance-sign table and for deciding which PENDING transactions
# count as "upcoming committed amounts" in the available-balance
# calculation.
DECREASING_TYPES = {TransactionType.EXPENSE, TransactionType.PAYMENT, TransactionType.MONEY_GIVEN}
INCREASING_TYPES = {TransactionType.INCOME, TransactionType.MONEY_RETURNED, TransactionType.REFUND}


def signed_effect(
    transaction_type: TransactionType,
    amount: Decimal,
    adjustment_direction: Optional[AdjustmentDirection] = None,
) -> Decimal:
    """
    Return the signed effect a (COMPLETED) transaction of this type/
    amount would have on the balance. `amount` is always the positive
    magnitude that was stored; the sign is derived entirely from the
    type (and, for ADJUSTMENT, the direction).
    """
    if transaction_type in INCREASING_TYPES:
        return amount
    if transaction_type in DECREASING_TYPES:
        return -amount
    if transaction_type == TransactionType.ADJUSTMENT:
        if adjustment_direction == AdjustmentDirection.DECREASE:
            return -amount
        return amount
    raise ValueError(f"Unknown transaction_type: {transaction_type}")


def new_transaction_document(
    user_id: str,
    transaction_type: TransactionType,
    amount: Decimal,
    transaction_date: date,
    status: TransactionStatus,
    category: Optional[str] = None,
    description: Optional[str] = None,
    person_name: Optional[str] = None,
    payment_method: Optional[PaymentMethod] = None,
    adjustment_direction: Optional[AdjustmentDirection] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Build the raw MongoDB document for a new transaction."""
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "transaction_type": transaction_type.value,
        "amount": to_decimal128(amount),
        "category": category.strip().upper() if category else None,
        "description": description.strip() if description else None,
        "person_name": person_name.strip() if person_name else None,
        "payment_method": payment_method.value if payment_method else None,
        "transaction_date": transaction_date.isoformat(),
        "status": status.value,
        "adjustment_direction": adjustment_direction.value if adjustment_direction else None,
        "notes": notes.strip() if notes else None,
        "created_at": now,
        "updated_at": now,
    }


def transaction_doc_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw MongoDB transaction document into the public API shape."""
    amount = from_decimal128(doc["amount"])
    tx_type = TransactionType(doc["transaction_type"])
    direction = AdjustmentDirection(doc["adjustment_direction"]) if doc.get("adjustment_direction") else None
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "transaction_type": tx_type,
        "amount": amount,
        "signed_amount": signed_effect(tx_type, amount, direction) if doc["status"] == TransactionStatus.COMPLETED.value else Decimal("0.00"),
        "category": doc.get("category"),
        "description": doc.get("description"),
        "person_name": doc.get("person_name"),
        "payment_method": doc.get("payment_method"),
        "transaction_date": doc["transaction_date"],
        "status": TransactionStatus(doc["status"]),
        "adjustment_direction": direction,
        "notes": doc.get("notes"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


def new_starting_balance_document(
    user_id: str,
    amount: Decimal,
    balance_date: date,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "amount": to_decimal128(amount),
        "date": balance_date.isoformat(),
        "notes": notes.strip() if notes else None,
        "created_at": now,
        "updated_at": now,
    }


def starting_balance_doc_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "amount": from_decimal128(doc["amount"]),
        "date": doc["date"],
        "notes": doc.get("notes"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }
