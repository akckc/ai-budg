from datetime import date, timedelta
from typing import Optional
from db import get_db
from services.transaction_service import get_all_transactions
from services.forecast_service import (
    get_active_recurring_events,
    get_occurrences_in_window,
)
from models.projection_dto import DailyProjection, ProjectionResult


def _is_consumed(event_id: int, occ_date: date, consumed_map: dict) -> bool:
    """Return True if a transaction linked to event_id exists within ±3 days of occ_date."""
    tx_dates = consumed_map.get(event_id, [])
    for tx_date in tx_dates:
        if abs((tx_date - occ_date).days) <= 3:
            return True
    return False


def calculate_two_week_projection(as_of_date: Optional[date] = None, days: int = 14) -> ProjectionResult:
    """Deterministic N-day projection as defined by DA v1.1.

    Pure function of ledger state, recurring templates, and an optional reference date.
    If ``as_of_date`` is not provided, defaults to ``date.today()``.
    ``days`` controls the forecast window length (default 14).
    No writes, no side effects, inclusive window definition.
    """
    today = as_of_date if as_of_date is not None else date.today()
    end_date = today + timedelta(days=days)

    # --- starting balance via service/repository chain ---
    txs = get_all_transactions()
    # amount is the 5th column in the repository's SELECT
    starting_balance = sum(tx[4] for tx in txs)

    # --- fetch active recurring templates and consumed transactions ---
    conn = get_db()
    try:
        events = get_active_recurring_events(conn)

        # Query transactions linked to recurring events in the window (±3 day buffer)
        consumed_rows = conn.execute("""
            SELECT recurring_event_id, date
            FROM transactions
            WHERE recurring_event_id IS NOT NULL
              AND date BETWEEN ? AND ?
        """, [today - timedelta(days=3), end_date + timedelta(days=3)]).fetchall()
    finally:
        conn.close()

    # Build consumed map: {event_id: [date, ...]}
    consumed_map: dict = {}
    for event_id, tx_date in consumed_rows:
        consumed_map.setdefault(int(event_id), []).append(tx_date)

    # --- prepare daily buckets ---
    daily_deltas = {}
    iter_day = today
    while iter_day <= end_date:
        daily_deltas[iter_day] = 0.0
        iter_day += timedelta(days=1)

    total_upcoming = 0.0
    for event in events:
        allow_consume = event.get('allow_consume', True)
        occurrences = get_occurrences_in_window(event, today, window_days=days)
        for occ in occurrences:
            if allow_consume and _is_consumed(int(event['id']), occ, consumed_map):
                continue
            daily_deltas[occ] += event['amount']
            total_upcoming += event['amount']

    # --- build timeline ---
    timeline = []
    running = starting_balance
    for d in sorted(daily_deltas.keys()):
        running += daily_deltas[d]
        timeline.append(DailyProjection(date=d, projected_balance=running))

    safe_to_spend = starting_balance + total_upcoming

    return ProjectionResult(
        start_date=today,
        end_date=end_date,
        starting_balance=starting_balance,
        timeline=timeline,
        safe_to_spend=safe_to_spend,
    )
