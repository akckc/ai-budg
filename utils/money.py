from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def parse_money(value: str) -> Decimal:
    if value is None:
        raise ValueError("missing money value")

    normalized = value.strip()
    if not normalized:
        raise ValueError("empty money value")

    is_negative = normalized.startswith("(") and normalized.endswith(")")
    normalized = normalized.replace("$", "").replace(",", "")

    if is_negative:
        normalized = normalized[1:-1]

    try:
        amount = Decimal(normalized).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
    except InvalidOperation as exc:
        raise ValueError("invalid money value") from exc

    return -amount if is_negative else amount