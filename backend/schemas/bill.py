"""
schemas/bill.py

Pydantic request/response schemas for STEP 4 Payment/Bill scheduling
(recurring + one-off scheduled payments), extended in STEP 6 with
reminders, priority, and computed due-status/summary shapes.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from models.bill import BillFrequency, BillPriority, BillStatus, DueStatus
from models.transaction import PaymentMethod


class BillCreateRequest(BaseModel):
    """Payload for POST /api/bills."""

    name: str = Field(min_length=1, max_length=120, description="Title of the payment/reminder, e.g. 'Rent'.")
    description: Optional[str] = Field(default=None, max_length=500)
    amount: Decimal = Field(gt=0, decimal_places=2)
    due_date: date = Field(description="Next (or only, for one-off) due date.")
    is_recurring: bool
    frequency: Optional[BillFrequency] = Field(default=None, description="Required when is_recurring is True.")
    category: Optional[str] = Field(default=None, max_length=50)
    payment_method: Optional[PaymentMethod] = None
    person_name: Optional[str] = Field(default=None, max_length=120)
    priority: BillPriority = BillPriority.MEDIUM
    reminder_enabled: bool = False
    reminder_date: Optional[date] = Field(default=None, description="Required when reminder_enabled is True.")
    notes: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_frequency(self) -> "BillCreateRequest":
        if self.is_recurring and self.frequency is None:
            raise ValueError("frequency is required when is_recurring is True")
        if not self.is_recurring and self.frequency is not None:
            raise ValueError("frequency must not be set when is_recurring is False")
        if self.reminder_enabled and self.reminder_date is None:
            raise ValueError("reminder_date is required when reminder_enabled is True")
        if self.reminder_date is not None and self.reminder_date > self.due_date:
            raise ValueError("reminder_date must be on or before due_date")
        return self


class BillUpdateRequest(BaseModel):
    """Payload for PATCH /api/bills/{bill_id}. All fields optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    due_date: Optional[date] = None
    frequency: Optional[BillFrequency] = None
    category: Optional[str] = Field(default=None, max_length=50)
    payment_method: Optional[PaymentMethod] = None
    person_name: Optional[str] = Field(default=None, max_length=120)
    status: Optional[BillStatus] = None
    priority: Optional[BillPriority] = None
    reminder_enabled: Optional[bool] = None
    reminder_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class BillPayRequest(BaseModel):
    """Payload for POST /api/bills/{bill_id}/pay. Defaults to today if payment_date is omitted."""

    payment_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class BillPublic(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    amount: Decimal
    category: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    person_name: Optional[str] = None
    is_recurring: bool
    frequency: Optional[BillFrequency] = None
    due_date: str
    status: BillStatus = Field(description="Schedule lifecycle status: ACTIVE/PAUSED/CANCELLED/COMPLETED.")
    due_status: DueStatus = Field(
        description="Computed personal payment status: UPCOMING/DUE/OVERDUE/PAID/CANCELLED. Never stored — derived from status + due_date."
    )
    priority: BillPriority = BillPriority.MEDIUM
    reminder_enabled: bool = False
    reminder_date: Optional[str] = None
    last_paid_date: Optional[str] = None
    last_transaction_id: Optional[str] = Field(
        default=None, description="Id of the PAYMENT transaction created the last time this bill was paid."
    )
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BillListResponse(BaseModel):
    items: list[BillPublic]


class PaymentSummaryResponse(BaseModel):
    """Response for GET /api/bills/summary and GET /api/reports/payment-summary."""

    upcoming_count: int
    due_count: int
    overdue_count: int
    paid_count: int
    upcoming_amount: Decimal
    due_amount: Decimal
    overdue_amount: Decimal


class MonthlyUpcomingItem(BaseModel):
    id: str
    name: str
    amount: Decimal
    due_date: str


class MonthlyUpcomingTotalResponse(BaseModel):
    """Response for GET /api/bills/monthly-upcoming."""

    month: int
    year: int
    items: list[MonthlyUpcomingItem]
    total: Decimal
