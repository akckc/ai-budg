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


def get_active_recurring_monthly_by_category(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            category,
            SUM(ABS(amount) * CASE frequency
                WHEN 'monthly'  THEN 1.0
                WHEN 'weekly'   THEN 4.33
                WHEN 'biweekly' THEN 2.167
                WHEN 'annual'   THEN 0.08333
                ELSE 0.0
            END) AS monthly_equivalent
        FROM recurring_events
        WHERE active = TRUE
          AND category IS NOT NULL
        GROUP BY category
        """
    ).fetchall()
    return [{"category": r[0], "monthly_equivalent": round(float(r[1]), 2)} for r in rows]
