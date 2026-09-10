"""
schemas/money_given.py

Pydantic request/response schemas for STEP 5 "Money Given & Money
Returned" tracking.

All monetary fields use Decimal (never float) so amounts are never
subject to binary floating-point rounding — see utils/money.py.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from models.money_given import MoneyGivenCategory, MoneyGivenStatus
from models.transaction import PaymentMethod

# ---------------------------------------------------------------------
# Money given — requests
# ---------------------------------------------------------------------


class MoneyGivenCreateRequest(BaseModel):
    """Payload for POST /api/money-given."""

    person_name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, decimal_places=2, description="Must be greater than zero.")
    reason: Optional[str] = Field(default=None, max_length=500)
    category: Optional[MoneyGivenCategory] = None
    payment_method: Optional[PaymentMethod] = None
    given_date: date
    expected_return_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_expected_return_date(self) -> "MoneyGivenCreateRequest":
        if self.expected_return_date is not None and self.expected_return_date < self.given_date:
            raise ValueError("expected_return_date cannot be before given_date")
        return self


class MoneyGivenUpdateRequest(BaseModel):
    """
    Payload for PATCH /api/money-given/{money_given_id}. All fields
    optional. Deliberately excludes amount_given, amount_returned,
    outstanding_amount, and status — those only ever change through
    POST .../return or DELETE (cancel), which keep them consistent
    with the linked Step 3 transactions (spec section 11).
    """

    person_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    reason: Optional[str] = Field(default=None, max_length=500)
    category: Optional[MoneyGivenCategory] = None
    expected_return_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class MoneyReturnRequest(BaseModel):
    """Payload for POST /api/money-given/{money_given_id}/return."""

    amount: Decimal = Field(gt=0, decimal_places=2, description="Must be greater than zero and not exceed the current outstanding amount.")
    return_date: date
    payment_method: Optional[PaymentMethod] = None
    notes: Optional[str] = Field(default=None, max_length=500)


# ---------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------


class MoneyReturnPublic(BaseModel):
    id: str
    money_given_id: str
    user_id: str
    amount: Decimal
    return_date: str
    payment_method: Optional[PaymentMethod] = None
    notes: Optional[str] = None
    return_transaction_id: Optional[str] = Field(
        default=None, description="Id of the MONEY_RETURNED transaction created for this return."
    )
    created_at: datetime
    updated_at: datetime


class MoneyReturnListResponse(BaseModel):
    items: list[MoneyReturnPublic]


class MoneyGivenPublic(BaseModel):
    id: str
    user_id: str
    person_name: str
    amount_given: Decimal
    amount_returned: Decimal
    outstanding_amount: Decimal
    reason: Optional[str] = None
    category: Optional[MoneyGivenCategory] = None
    payment_method: Optional[PaymentMethod] = None
    given_date: str
    expected_return_date: Optional[str] = None
    status: MoneyGivenStatus
    notes: Optional[str] = None
    given_transaction_id: Optional[str] = Field(
        default=None, description="Id of the MONEY_GIVEN transaction created when this record was made."
    )
    created_at: datetime
    updated_at: datetime
    returns: Optional[list[MoneyReturnPublic]] = Field(
        default=None, description="Return history, included on the single-record GET endpoint."
    )


class MoneyGivenListResponse(BaseModel):
    items: list[MoneyGivenPublic]
    total: int
    page: int
    page_size: int


class MoneyGivenSummaryResponse(BaseModel):
    total_money_given: Decimal
    total_money_returned: Decimal
    total_outstanding: Decimal
    active_records: int
    settled_records: int


class PersonSummaryItem(BaseModel):
    person_name: str
    total_given: Decimal
    total_returned: Decimal
    outstanding: Decimal


class PersonSummaryResponse(BaseModel):
    people: list[PersonSummaryItem]
