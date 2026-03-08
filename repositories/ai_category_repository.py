from db import get_db


def list_uncategorized_merchants(conn, limit: int) -> list[str]:
    """
    Return distinct merchant_normalized values where category IS NULL.
    Deterministic read-only.
    """
    query = """
        SELECT DISTINCT merchant_normalized
        FROM transactions
        WHERE category IS NULL
          AND merchant_normalized IS NOT NULL
          AND merchant_normalized != ''
        ORDER BY merchant_normalized
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    
    rows = conn.execute(query).fetchall()
    return [row[0] for row in rows]


def get_cached_suggestion(conn, merchant_normalized: str) -> str | None:
    """
    Return cached suggested_category for merchant, or None if not cached.
    Deterministic read.
    """
    row = conn.execute(
        "SELECT suggested_category FROM ai_category_suggestions WHERE merchant_normalized = ?",
        [merchant_normalized]
    ).fetchone()
    return row[0] if row else None


def upsert_suggestion(conn, merchant_normalized: str, category: str, model: str) -> None:
    """
    Insert or update cached suggestion using ON CONFLICT.
    No side effects on read.
    """
    conn.execute(
        """
        INSERT INTO ai_category_suggestions (merchant_normalized, suggested_category, model)
        VALUES (?, ?, ?)
        ON CONFLICT(merchant_normalized) DO UPDATE SET
            suggested_category = excluded.suggested_category,
            model = excluded.model,
            created_at = CURRENT_TIMESTAMP
        """,
        [merchant_normalized, category, model]
    )


def apply_suggestion_to_uncategorized(conn, merchant_normalized: str, category: str) -> int:
    """
    Bulk update category where category IS NULL and merchant_normalized matches.
    Return row count.
    """
    result = conn.execute(
        """
        UPDATE transactions
        SET category = ?
        WHERE merchant_normalized = ?
          AND category IS NULL
        """,
        [category, merchant_normalized]
    )
    return result.fetchone()[0] if hasattr(result, 'fetchone') else 0
