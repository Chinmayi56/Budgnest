"""
models/bill.py

Domain-level definitions for BudgetNest's STEP 4 Payment/Bill feature:
the "bills" collection.

A Bill represents a scheduled personal payment — either a recurring
bill (rent, subscriptions, EMIs, ...) or a one-off scheduled payment
(a single upcoming payment on a known date). Bills are purely
*schedule/plan* records: they never themselves affect the balance.
When a bill is marked paid, services/bill_service.py creates a real
PAYMENT transaction through the existing Step 3
services/financial_service.create_transaction — the single source of
truth for balance-affecting data stays the transactions collection,
never a second, competing ledger.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from utils.money import from_decimal128, to_decimal128

BILLS_COLLECTION = "bills"


class BillFrequency(str, Enum):
    """Only meaningful when is_recurring is True."""

    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class BillStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"  # one-off bills only, once paid


class BillPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DueStatus(str, Enum):
    """
    STEP 6 — computed (never stored) payment/reminder status, derived
    from the bill's lifecycle `status` (ACTIVE/PAUSED/CANCELLED/
    COMPLETED, set by services/bill_service.py) plus its due_date
    relative to today. This is intentionally a *derived* view rather
    than a second stored status field, so there is never a chance for
    the two statuses to drift out of sync.
    """

    UPCOMING = "UPCOMING"
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


def compute_due_status(bill_status: "BillStatus", due_date_str: str, today: Optional[date] = None) -> "DueStatus":
    """
    Derive the personal-facing DueStatus (spec section 4) from a
    bill's lifecycle status + due_date. Never stored — always computed
    fresh so it can't go stale.
    """
    if today is None:
        today = date.today()

    if bill_status == BillStatus.CANCELLED:
        return DueStatus.CANCELLED
    if bill_status == BillStatus.COMPLETED:
        return DueStatus.PAID
    # ACTIVE and PAUSED bills are judged purely by due_date. A PAUSED
    # bill is still "on the books" for reminder purposes but never
    # marked overdue/due since the user has explicitly paused it.
    due = date.fromisoformat(due_date_str)
    if bill_status == BillStatus.PAUSED:
        return DueStatus.UPCOMING
    if due < today:
        return DueStatus.OVERDUE
    if due == today:
        return DueStatus.DUE
    return DueStatus.UPCOMING


def _add_months(source: date, months: int) -> date:
    """Add whole calendar months to a date, clamping the day into the target month."""
    total_month_index = source.month - 1 + months
    year = source.year + total_month_index // 12
    month = total_month_index % 12 + 1
    # Clamp the day (e.g. Jan 31 + 1 month -> Feb 28/29, never Mar 3).
    if month == 12:
        days_in_month = 31
    else:
        days_in_month = (date(year, month + 1, 1) - date(year, month, 1)).days
    day = min(source.day, days_in_month)
    return date(year, month, day)


def next_due_date(current_due: date, frequency: BillFrequency) -> date:
    """Advance a recurring bill's due date by one occurrence of its frequency."""
    if frequency == BillFrequency.WEEKLY:
        return current_due + timedelta(weeks=1)
    if frequency == BillFrequency.BIWEEKLY:
        return current_due + timedelta(weeks=2)
    if frequency == BillFrequency.MONTHLY:
        return _add_months(current_due, 1)
    if frequency == BillFrequency.YEARLY:
        return _add_months(current_due, 12)
    raise ValueError(f"Unknown frequency: {frequency}")


def new_bill_document(
    user_id: str,
    name: str,
    amount: Decimal,
    due_date: date,
    is_recurring: bool,
    frequency: Optional[BillFrequency] = None,
    category: Optional[str] = None,
    payment_method: Optional[str] = None,
    person_name: Optional[str] = None,
    notes: Optional[str] = None,
    description: Optional[str] = None,
    priority: BillPriority = BillPriority.MEDIUM,
    reminder_enabled: bool = False,
    reminder_date: Optional[date] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "name": name.strip(),
        "description": description.strip() if description else None,
        "amount": to_decimal128(amount),
        "category": category.strip().upper() if category else None,
        "payment_method": payment_method,
        "person_name": person_name.strip() if person_name else None,
        "is_recurring": is_recurring,
        "frequency": frequency.value if frequency else None,
        "due_date": due_date.isoformat(),
        "status": BillStatus.ACTIVE.value,
        "priority": priority.value if priority else BillPriority.MEDIUM.value,
        "reminder_enabled": bool(reminder_enabled),
        "reminder_date": reminder_date.isoformat() if reminder_date else None,
        "last_paid_date": None,
        "last_transaction_id": None,
        "notes": notes.strip() if notes else None,
        "created_at": now,
        "updated_at": now,
    }


def bill_doc_to_dict(doc: dict[str, Any], today: Optional[date] = None) -> dict[str, Any]:
    status = BillStatus(doc["status"])
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "name": doc["name"],
        "description": doc.get("description"),
        "amount": from_decimal128(doc["amount"]),
        "category": doc.get("category"),
        "payment_method": doc.get("payment_method"),
        "person_name": doc.get("person_name"),
        "is_recurring": doc["is_recurring"],
        "frequency": BillFrequency(doc["frequency"]) if doc.get("frequency") else None,
        "due_date": doc["due_date"],
        "status": status,
        "due_status": compute_due_status(status, doc["due_date"], today),
        "priority": BillPriority(doc["priority"]) if doc.get("priority") else BillPriority.MEDIUM,
        "reminder_enabled": bool(doc.get("reminder_enabled", False)),
        "reminder_date": doc.get("reminder_date"),
        "last_paid_date": doc.get("last_paid_date"),
        "last_transaction_id": doc.get("last_transaction_id"),
        "notes": doc.get("notes"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }
