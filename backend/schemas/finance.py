"""
schemas/finance.py

Pydantic request/response schemas for the core personal financial
engine: starting balance, transactions, and financial summaries.

All monetary fields use Decimal (never float) so amounts are never
subject to binary floating-point rounding — see utils/money.py.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from models.transaction import (
    AdjustmentDirection,
    PaymentMethod,
    SUGGESTED_CATEGORIES,
    TransactionStatus,
    TransactionType,
)

# ---------------------------------------------------------------------
# Starting balance
# ---------------------------------------------------------------------


class StartingBalanceRequest(BaseModel):
    """Payload for POST /api/finance/starting-balance."""

    amount: Decimal = Field(gt=0, decimal_places=2, description="Must be greater than zero.")
    date: date
    notes: Optional[str] = Field(default=None, max_length=500)


class StartingBalanceAdjustRequest(BaseModel):
    """
    Payload for PATCH /api/finance/starting-balance.

    The explicit, intentional way to change an already-established
    starting balance (see 'Prevent accidental duplicate starting
    balances unless there is a clearly defined adjustment mechanism').
    """

    amount: Decimal = Field(gt=0, decimal_places=2, description="Must be greater than zero.")
    notes: Optional[str] = Field(default=None, max_length=500)


class StartingBalancePublic(BaseModel):
    id: str
    user_id: str
    amount: Decimal
    date: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------


class TransactionCreateRequest(BaseModel):
    """Payload for POST /api/transactions."""

    transaction_type: TransactionType
    amount: Decimal = Field(gt=0, decimal_places=2, description="Positive magnitude. Must be greater than zero.")
    category: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    person_name: Optional[str] = Field(default=None, max_length=120)
    payment_method: Optional[PaymentMethod] = None
    transaction_date: date
    status: TransactionStatus = TransactionStatus.COMPLETED
    adjustment_direction: Optional[AdjustmentDirection] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_adjustment_direction(self) -> "TransactionCreateRequest":
        if self.transaction_type == TransactionType.ADJUSTMENT and self.adjustment_direction is None:
            raise ValueError("adjustment_direction is required when transaction_type is ADJUSTMENT")
        if self.transaction_type != TransactionType.ADJUSTMENT and self.adjustment_direction is not None:
            raise ValueError("adjustment_direction is only valid when transaction_type is ADJUSTMENT")
        return self


class TransactionUpdateRequest(BaseModel):
    """
    Payload for PATCH /api/transactions/{transaction_id}.

    All fields optional — only supplied fields are changed. See
    routes/transactions.py for how updates to COMPLETED transactions
    are handled safely (balance never silently corrupted).
    """

    transaction_type: Optional[TransactionType] = None
    amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    category: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    person_name: Optional[str] = Field(default=None, max_length=120)
    payment_method: Optional[PaymentMethod] = None
    transaction_date: Optional[date] = None
    status: Optional[TransactionStatus] = None
    adjustment_direction: Optional[AdjustmentDirection] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def _amount_positive(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None and value <= 0:
            raise ValueError("amount must be greater than zero")
        return value


class TransactionPublic(BaseModel):
    id: str
    user_id: str
    transaction_type: TransactionType
    amount: Decimal
    signed_amount: Decimal = Field(description="Signed effect on balance; 0 unless status is COMPLETED.")
    category: Optional[str] = None
    description: Optional[str] = None
    person_name: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    transaction_date: str
    status: TransactionStatus
    adjustment_direction: Optional[AdjustmentDirection] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionPublic]
    total: int
    page: int
    page_size: int


class SuggestedCategoriesResponse(BaseModel):
    categories: list[str] = SUGGESTED_CATEGORIES


# ---------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------


class FinancialSummaryResponse(BaseModel):
    starting_balance: Decimal
    total_income: Decimal
    total_expenses: Decimal
    total_payments: Decimal
    total_money_given: Decimal
    total_money_returned: Decimal
    total_refunds: Decimal
    total_adjustments: Decimal
    current_balance: Decimal
    pending_commitments: Decimal = Field(description="Sum of PENDING expense/payment/money-given amounts.")
    available_balance: Decimal = Field(description="current_balance minus pending_commitments.")


class DailySummaryResponse(BaseModel):
    date: str
    total_income: Decimal
    total_expenses: Decimal
    total_payments: Decimal
    total_money_given: Decimal
    total_money_returned: Decimal
    total_refunds: Decimal
    transaction_count: int
    categories: dict[str, Decimal]


class MonthlySummaryResponse(BaseModel):
    month: int
    year: int
    total_income: Decimal
    total_expenses: Decimal
    total_payments: Decimal
    total_money_given: Decimal
    total_money_returned: Decimal
    total_refunds: Decimal
    transaction_count: int
    categories: dict[str, Decimal]
