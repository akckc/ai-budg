from db import get_db

# -----------------------------
# Transactions Repository
# -----------------------------

def insert_transaction(conn, account_name, date, description, amount,
                       balance=None, category=None, source='unknown',
                       user_id=None, merchant_id=None):
    """
    Inserts a transaction into the DB for the given account.
    - conn: DuckDB connection (from get_db() or passed in)
    - account_name: str, optional, defaults to Primary Account if None
    """

    if not account_name:
        account_name = "Primary Account"

    # Ensure account exists
    account_row = conn.execute(
        "SELECT id FROM accounts WHERE account_name = ?", (account_name,)
    ).fetchone()

    if account_row:
        account_id = account_row[0]
    else:
        # create account on the fly
        conn.execute(
            "INSERT INTO accounts (account_name) VALUES (?)", (account_name,)
        )
        account_id = conn.execute(
            "SELECT id FROM accounts WHERE account_name = ?", (account_name,)
        ).fetchone()[0]

    try:
        conn.execute(
            """
            INSERT INTO transactions
            (account_id, date, description, amount, balance, category, source, user_id, merchant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (account_id, date, description, amount, balance, category, source, user_id, merchant_id)
        )
    except Exception as e:
        # Check if exception is a unique constraint violation (duplicate)
        msg = str(e).lower()
        if "unique" in msg:
            raise ValueError("Duplicate transaction (unique constraint)")
        else:
            raise

def transaction_exists(conn, account_name, date, description, amount):
    """
    Checks if a transaction already exists.
    """
    if not account_name:
        account_name = "Primary Account"

    row = conn.execute(
        """
        SELECT 1
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.account_name = ? AND t.date = ? AND t.description = ? AND t.amount = ?
        """,
        (account_name, date, description, amount)
    ).fetchone()

    return bool(row)