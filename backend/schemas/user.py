"""
schemas/user.py

Pydantic request/response schemas for authentication and user data.
These are the shapes exposed over the API — kept separate from the raw
MongoDB document shape in models/user.py.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from models.user import UserRole, UserStatus


class UserRegisterRequest(BaseModel):
    """
    Payload for POST /api/auth/register.

    BudgetNest has a single application role (USER), so role is not a
    client-supplied field: every self-registered account is created as
    UserRole.USER by the route/service layer, never from client input.
    """

    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("full_name cannot be empty")
        return value


class UserLoginRequest(BaseModel):
    """Payload for POST /api/auth/login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    """Safe, outward-facing user representation. Never includes password_hash."""

    id: str
    full_name: str
    email: EmailStr
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """Payload returned by POST /api/auth/login."""

    access_token: str
    token_type: str = "bearer"
    user: UserPublic

class SendLoginCodeRequest(BaseModel):
    email: EmailStr


class VerifyLoginCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
