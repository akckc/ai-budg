import duckdb
from duckdb import IntegrityError

DB_FILE = "budget.duckdb"

def insert_transaction(account_id: int, date, description: str, amount, balance=None, category=None, source="unknown", user_id=None, merchant_id=None):
    """
    Insert a transaction row into the DB.
    Raises IntegrityError on UNIQUE constraint violation.
    """
    conn = duckdb.connect(DB_FILE)
    try:
        conn.execute(
            """
            INSERT INTO transactions 
                (account_id, date, description, amount, balance, category, source, user_id, merchant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (account_id, date, description, amount, balance, category, source, user_id, merchant_id)
        )
    finally:
        conn.close()