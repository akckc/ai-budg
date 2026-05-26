def list_orphan_groups(conn) -> list[dict]:
    """Transaction categories that exist in no category_budgets row."""
    rows = conn.execute("""
        SELECT t.category, COUNT(*) AS tx_count
        FROM transactions t
        WHERE t.category IS NOT NULL
          AND t.category NOT IN (SELECT category_name FROM category_budgets)
        GROUP BY t.category
        ORDER BY t.category
    """).fetchall()
    return [{"category": r[0], "tx_count": r[1]} for r in rows]


def bulk_reclassify(conn, current_category: str, new_category: str) -> int:
    """Reassigns all transactions from current_category to new_category. Returns count updated."""
    row = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE category = ?",
        (current_category,),
    ).fetchone()
    count = row[0] if row else 0
    conn.execute(
        "UPDATE transactions SET category = ? WHERE category = ?",
        (new_category, current_category),
    )
    return count
