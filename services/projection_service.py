from datetime import date, timedelta
from db import get_db
from services.transaction_service import get_all_transactions
from services.forecast_service import (
    get_active_recurring_events,
    get_occurrences_in_window,
)
from models.projection_dto import DailyProjection, ProjectionResult


def calculate_two_week_projection() -> ProjectionResult:
    """Deterministic 14-day projection as defined by DA v1.1.

    Pure function of ledger state, recurring templates, and ``date.today()``.
    No writes, no side effects, inclusive window definition.
    """
    today = date.today()
    end_date = today + timedelta(days=14)

    # --- starting balance via service/repository chain ---
    txs = get_all_transactions()
    # amount is the 5th column in the repository's SELECT
    starting_balance = sum(tx[4] for tx in txs)

    # --- fetch active recurring templates ---
    conn = get_db()
    try:
        events = get_active_recurring_events(conn)
    finally:
        conn.close()

    # --- prepare daily buckets ---
    daily_deltas = {}
    iter_day = today
    while iter_day <= end_date:
        daily_deltas[iter_day] = 0.0
        iter_day += timedelta(days=1)

    total_upcoming = 0.0
    for event in events:
        occurrences = get_occurrences_in_window(event, today, window_days=14)
        for occ in occurrences:
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
