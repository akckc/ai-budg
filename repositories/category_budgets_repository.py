from db import get_db


def upsert_category_budget(category_name: str, monthly_budget: float, active: bool) -> None:
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO category_budgets (category_name, monthly_budget, active)
            VALUES (?, ?, ?)
            ON CONFLICT(category_name)
            DO UPDATE SET monthly_budget = excluded.monthly_budget,
                          active = excluded.active
            """,
            (category_name, monthly_budget, active),
        )
    finally:
        conn.close()


def get_all_category_budgets() -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category_name, monthly_budget, active
            FROM category_budgets
            """
        ).fetchall()

        return [
            {
                "category_name": r[0],
                "monthly_budget": r[1],
                "active": r[2],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_spend_grouped_by_category() -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category, SUM(amount)
            FROM transactions
            GROUP BY category
            """
        ).fetchall()

        return [
            {
                "category_name": r[0],
                "current_spend": float(r[1]) if r[1] is not None else 0.0,
            }
            for r in rows
        ]
    finally:
        conn.close()
