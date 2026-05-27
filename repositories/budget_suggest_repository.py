from datetime import date, timedelta


def get_90day_spend_by_category(conn) -> list[dict]:
    cutoff = date.today() - timedelta(days=90)
    rows = conn.execute(
        """
        SELECT category, SUM(amount)
        FROM transactions
        WHERE date >= ?
          AND amount < 0
          AND category IS NOT NULL
        GROUP BY category
        """,
        (cutoff,),
    ).fetchall()
    return [{"category": r[0], "total_spend": abs(float(r[1]))} for r in rows]
