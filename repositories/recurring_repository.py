from db import get_db


def create_recurring_event(
    *,
    account_id: int,
    name: str,
    amount: float,
    category: str | None,
    frequency: str,
    day_of_month: int | None,
    anchor_date: str,
    active: bool,
) -> int:
    """
    Insert a new row into recurring_events and return the new id.

    Implementation requirements:
    - Use DuckDB connection from db.get_db() inside this repository only.
    - Use recurring_events_id_seq for IDs:
      - either set DEFAULT in schema, or
      - INSERT with nextval('recurring_events_id_seq').
    - Store anchor_date into the DB as DATE.
    - No side effects beyond the insert.
    """
    conn = get_db()
    try:
        row = conn.execute(
            """
            INSERT INTO recurring_events (
                id,
                account_id,
                name,
                amount,
                category,
                frequency,
                day_of_month,
                anchor_date,
                active
            )
            VALUES (
                nextval('recurring_events_id_seq'),
                ?, ?, ?, ?, ?, ?, CAST(? AS DATE), ?
            )
            RETURNING id
            """,
            [
                account_id,
                name,
                amount,
                category,
                frequency,
                day_of_month,
                anchor_date,
                active,
            ],
        ).fetchone()
        return int(row[0])
    finally:
        conn.close()


def list_recurring_events(*, include_inactive: bool = True) -> list[dict]:
    """
    Return recurring events as a list of dicts, including account_name if possible via join.

    Required keys in each dict:
    - id, account_id, account_name, name, amount, category, frequency, day_of_month, anchor_date, active
    """
    conn = get_db()
    try:
        query = """
            SELECT
                re.id,
                re.account_id,
                COALESCE(a.account_name, '') AS account_name,
                re.name,
                re.amount,
                re.category,
                re.frequency,
                re.day_of_month,
                re.anchor_date,
                re.active
            FROM recurring_events re
            LEFT JOIN accounts a ON a.id = re.account_id
        """
        params = []
        if not include_inactive:
            query += " WHERE re.active = TRUE"
        query += " ORDER BY re.id"

        rows = conn.execute(query, params).fetchall()
        events = []
        for row in rows:
            anchor = row[8]
            events.append(
                {
                    "id": int(row[0]),
                    "account_id": int(row[1]),
                    "account_name": row[2],
                    "name": row[3],
                    "amount": float(row[4]),
                    "category": row[5],
                    "frequency": row[6],
                    "day_of_month": row[7],
                    "anchor_date": anchor.isoformat() if anchor else None,
                    "active": bool(row[9]),
                }
            )

        return events
    finally:
        conn.close()


def set_recurring_event_active(*, event_id: int, active: bool) -> None:
    """
    Update recurring_events.active for the given id.
    """
    conn = get_db()
    try:
        conn.execute(
            "UPDATE recurring_events SET active = ? WHERE id = ?",
            [active, event_id],
        )
    finally:
        conn.close()
