"""
schemas/budget.py

Pydantic request/response schemas for STEP 4 personal budgets
(overall + per-category monthly spending limits).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from models.budget import BudgetStatus, BudgetType


class BudgetCreateRequest(BaseModel):
    """Payload for POST /api/budgets."""

    budget_type: BudgetType
    category: Optional[str] = Field(default=None, max_length=50, description="Required when budget_type is CATEGORY.")
    limit_amount: Decimal = Field(gt=0, decimal_places=2)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    notes: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_category(self) -> "BudgetCreateRequest":
        if self.budget_type == BudgetType.CATEGORY and not self.category:
            raise ValueError("category is required when budget_type is CATEGORY")
        if self.budget_type == BudgetType.OVERALL and self.category:
            raise ValueError("category must not be set when budget_type is OVERALL")
        return self


class BudgetUpdateRequest(BaseModel):
    """Payload for PATCH /api/budgets/{budget_id}. Only limit_amount/notes may change."""

    limit_amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    notes: Optional[str] = Field(default=None, max_length=500)


class BudgetPublic(BaseModel):
    id: str
    user_id: str
    budget_type: BudgetType
    category: Optional[str] = None
    limit_amount: Decimal
    month: int
    year: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BudgetWithUsage(BudgetPublic):
    spent_amount: Decimal = Field(description="Computed live from Step 3's monthly summary — never stored.")
    remaining_amount: Decimal
    percentage_used: float
    budget_status: BudgetStatus


class BudgetListResponse(BaseModel):
    items: list[BudgetWithUsage]
