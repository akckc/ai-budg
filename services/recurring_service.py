from datetime import date

from repositories.recurring_repository import (
    create_recurring_event,
    list_recurring_events,
    set_recurring_event_active,
)

ALLOWED_FREQUENCIES = ("monthly", "biweekly")


def add_recurring_event(payload: dict) -> int:
    """
    Validate/normalize input and create the recurring event via repository.
    Returns the new id.

    Validation rules (minimal):
    - account_id required int
    - name required non-empty str
    - amount required float (can be positive or negative)
    - frequency required and must be in ALLOWED_FREQUENCIES
    - anchor_date required ISO date string YYYY-MM-DD (always required due to schema)
    - if frequency == 'monthly': day_of_month required int 1..31
    - if frequency == 'biweekly': day_of_month must be None (or ignored)
    - category optional
    - active default True
    """
    if "account_id" not in payload:
        raise ValueError("account_id is required")
    try:
        account_id = int(payload["account_id"])
    except (TypeError, ValueError):
        raise ValueError("account_id must be an int")

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name is required")
    name = name.strip()

    if "amount" not in payload:
        raise ValueError("amount is required")
    try:
        amount = float(payload["amount"])
    except (TypeError, ValueError):
        raise ValueError("amount must be a float")

    frequency = payload.get("frequency")
    if not isinstance(frequency, str):
        raise ValueError("frequency is required")
    frequency = frequency.strip().lower()
    if frequency not in ALLOWED_FREQUENCIES:
        raise ValueError("frequency must be monthly or biweekly")

    anchor_date = payload.get("anchor_date")
    if not isinstance(anchor_date, str) or not anchor_date.strip():
        raise ValueError("anchor_date is required")
    anchor_date = anchor_date.strip()
    try:
        date.fromisoformat(anchor_date)
    except ValueError:
        raise ValueError("anchor_date must be YYYY-MM-DD")

    day_of_month = payload.get("day_of_month")
    if frequency == "monthly":
        if day_of_month is None:
            raise ValueError("day_of_month is required for monthly frequency")
        try:
            day_of_month = int(day_of_month)
        except (TypeError, ValueError):
            raise ValueError("day_of_month must be an int")
        if day_of_month < 1 or day_of_month > 31:
            raise ValueError("day_of_month must be between 1 and 31")
    else:
        day_of_month = None

    category = payload.get("category")
    if category is not None:
        category = str(category).strip()
        if category == "":
            category = None

    active = payload.get("active", True)
    if isinstance(active, str):
        active = active.strip().lower() in ("1", "true", "yes", "on")
    else:
        active = bool(active)

    return create_recurring_event(
        account_id=account_id,
        name=name,
        amount=amount,
        category=category,
        frequency=frequency,
        day_of_month=day_of_month,
        anchor_date=anchor_date,
        active=active,
    )


def get_recurring_events(*, include_inactive: bool = True) -> dict:
    """
    Return JSON-safe structure:
    { "count": <int>, "events": <list[dict]> }
    using repository.list_recurring_events().
    """
    events = list_recurring_events(include_inactive=include_inactive)
    return {"count": len(events), "events": events}


def toggle_recurring_event_active(*, event_id: int, active: bool) -> None:
    """
    Set active flag via repository.
    """
    set_recurring_event_active(event_id=event_id, active=active)
