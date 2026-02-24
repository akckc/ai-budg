### Forecast service looks ahead in recurring transactions and predicts future cash flow based on known patterns.
from datetime import date, timedelta
from math import ceil

def get_active_recurring_events(conn):
    result = conn.execute("""
        SELECT *
        FROM recurring_events
        WHERE active = TRUE
    """)

    columns = [col[0] for col in result.description]
    rows = result.fetchall()

    return [dict(zip(columns, row)) for row in rows]

def get_current_balance(conn):
    return conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions").fetchone()[0]

def get_occurrences_in_window(event, today, window_days=14):
    occurrences = []
    window_end = today + timedelta(days=window_days)

    if event['frequency'] == 'monthly':
        # Determine this month's occurrence
        day = event['day_of_month']
        year = today.year
        month = today.month
        try:
            occ_date = date(year, month, day)
        except ValueError:
            # clamp to last day of month
            from calendar import monthrange
            last_day = monthrange(year, month)[1]
            occ_date = date(year, month, min(day, last_day))
        if occ_date < today:
            # move to next month
            month += 1
            if month > 12:
                month = 1
                year += 1
            try:
                occ_date = date(year, month, day)
            except ValueError:
                last_day = monthrange(year, month)[1]
                occ_date = date(year, month, min(day, last_day))
        if today <= occ_date <= window_end:
            occurrences.append(occ_date)

    elif event['frequency'] == 'biweekly':
        anchor = event['anchor_date']
        # number of 14-day cycles since anchor
        days_since_anchor = (today - anchor).days
        cycles = ceil(days_since_anchor / 14) if days_since_anchor > 0 else 0
        next_date = anchor + timedelta(days=cycles * 14)
        while next_date <= window_end:
            if next_date >= today:
                occurrences.append(next_date)
            next_date += timedelta(days=14)

    return occurrences

def calculate_two_week_forecast(conn, today=None):
    if today is None:
        today = date.today()

    current_balance = get_current_balance(conn)
    events = get_active_recurring_events(conn)

    upcoming_total = 0
    upcoming_items = []

    for event in events:
        for occ_date in get_occurrences_in_window(event, today):
            upcoming_total += event['amount']
            upcoming_items.append({
                "name": event['name'],
                "date": occ_date,
                "amount": event['amount']
            })

    projected_balance = current_balance + upcoming_total

    return {
        "current_balance": current_balance,
        "upcoming_total": upcoming_total,
        "projected_balance": projected_balance,
        "items": sorted(upcoming_items, key=lambda x: x["date"])
    }