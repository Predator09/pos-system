from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def decimal_money(value) -> Decimal:
    """Convert any numeric-ish value to Decimal dollars."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def to_cents(value) -> int:
    """Convert dollars to integer cents using half-up rounding."""
    amt = decimal_money(value).quantize(CENT, rounding=ROUND_HALF_UP)
    return int((amt * HUNDRED).to_integral_value(rounding=ROUND_HALF_UP))


def cents_to_float(cents: int | None) -> float:
    """Convert integer cents to 2-decimal float for UI/back-compat payloads."""
    raw = int(cents or 0)
    return float((Decimal(raw) / HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP))
