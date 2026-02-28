from db import get_db


def get_all_category_rules(conn=None):
    """
    Return all category rules sorted by id (priority).

    Args:
        conn: Optional database connection. If not provided, opens a new one.

    Returns:
        List of rule dicts with 'id', 'pattern', and 'category' keys.

    Repository-level function: no rule evaluation logic.
    """
    own_conn = False
    if conn is None:
        conn = get_db()
        own_conn = True

    try:
        rows = conn.execute("""
            SELECT id, pattern, category
            FROM category_rules
            ORDER BY id
        """).fetchall()

        rules = [
            {
                "id": r[0],
                "pattern": r[1],
                "category": r[2]
            }
            for r in rows
        ]

        return rules
    finally:
        if own_conn:
            conn.close()


def get_rule_by_id(conn, rule_id):
    """
    Return a single rule by ID.

    Args:
        conn: Database connection.
        rule_id: ID of the rule to fetch.

    Returns:
        Rule dict or None if not found.
    """
    row = conn.execute(
        "SELECT id, pattern, category FROM category_rules WHERE id = ?",
        (rule_id,)
    ).fetchone()

    if row:
        return {
            "id": row[0],
            "pattern": row[1],
            "category": row[2]
        }
    return None


def add_category_rule(conn, pattern, category):
    """
    Insert a new category rule.

    Args:
        conn: Database connection.
        pattern: Pattern string to match.
        category: Category to assign on match.
    """
    conn.execute(
        "INSERT INTO category_rules (pattern, category) VALUES (?, ?)",
        (pattern, category)
    )


def delete_rule(conn, rule_id):
    """
    Delete a rule by ID.

    Args:
        conn: Database connection.
        rule_id: ID of the rule to delete.
    """
    conn.execute(
        "DELETE FROM category_rules WHERE id = ?",
        (rule_id,)
    )
