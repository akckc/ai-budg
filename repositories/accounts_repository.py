from db import get_db

# -----------------------------
# Accounts Repository
# -----------------------------

def get_or_create_account(account_name: str):
    """Return the account row for the given name, creating it if missing.

    The caller expects a mapping with at least an ``"id"`` key so that
    routes can reference ``account["id"]``.  ``None`` or an empty string
    is normalized to the default "Primary Account".
    """
    if not account_name:
        account_name = "Primary Account"

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, account_name FROM accounts WHERE account_name = ?",
            (account_name,)
        ).fetchone()
        if row:
            # DuckDB rows behave like tuples; convert to dict for caller convenience
            return {"id": row[0], "account_name": row[1]}

        # not found; create and fetch
        conn.execute(
            "INSERT INTO accounts (account_name) VALUES (?)",
            (account_name,)
        )
        row = conn.execute(
            "SELECT id, account_name FROM accounts WHERE account_name = ?",
            (account_name,)
        ).fetchone()
        return {"id": row[0], "account_name": row[1]}
    finally:
        conn.close()


def list_accounts():
    """Return a list of all accounts as dicts."""
    conn = get_db()
    try:
        rows = conn.execute("SELECT id, account_name FROM accounts ORDER BY account_name").fetchall()
        return [{"id": r[0], "account_name": r[1]} for r in rows]
    finally:
        conn.close()
