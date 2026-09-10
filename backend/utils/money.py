"""
utils/money.py

Safe monetary representation helpers.

All financial arithmetic in BudgetNest is done with Python's Decimal
type, and stored in MongoDB using BSON's Decimal128 (a true
base-10 decimal type), never as an ordinary MongoDB `double`. This
avoids the classic binary floating-point problem where repeated
arithmetic on amounts produces values like 100.0000000001 instead of
100.00.

Rule of thumb used everywhere in the financial engine:
    MongoDB double  -> never
    MongoDB Decimal128 -> storage
    Python Decimal      -> all calculations
    JSON (API response) -> Decimal serializes as an exact numeric
                            string (e.g. "59000.00"), so clients never
                            see binary floating-point rounding either.
"""

from decimal import ROUND_HALF_UP, Decimal

from bson import Decimal128

TWO_PLACES = Decimal("0.01")


def quantize_amount(value: Decimal | float | int | str) -> Decimal:
    """Round a value to exactly 2 decimal places using round-half-up."""
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def to_decimal128(value: Decimal | float | int | str) -> Decimal128:
    """Convert a Python Decimal (or decimal-like value) to BSON Decimal128 for storage."""
    return Decimal128(quantize_amount(value))


def from_decimal128(value: Decimal128 | Decimal | float | int | None) -> Decimal:
    """Convert a stored Decimal128 (or already-Decimal value) back to a Python Decimal."""
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal128):
        return value.to_decimal()
    return quantize_amount(value)
