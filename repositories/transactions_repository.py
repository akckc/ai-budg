from db import get_db

def transaction_exists(date, description, amount, balance):
    conn = get_db()
    exists = conn.execute("""
        SELECT 1 FROM transactions
        WHERE date = ?
          AND description = ?
          AND amount = ?
          AND balance = ?
    """, [date, description, amount, balance]).fetchone()
    conn.close()
    return exists is not None


def insert_transaction(date, description, amount, balance):
    conn = get_db()
    conn.execute("""
        INSERT INTO transactions
        (date, description, amount, balance, category, source)
        VALUES (?, ?, ?, ?, NULL, 'csv')
    """, [date, description, amount, balance])
    conn.close()


def get_all_transactions():
    conn = get_db()
    result = conn.execute("""
        SELECT id, date, description, amount, balance, category
        FROM transactions
        ORDER BY date DESC
    """).fetchall()
    conn.close()
    return result


def update_category(transaction_id, category):
    conn = get_db()
    conn.execute("""
        UPDATE transactions
        SET category = ?
        WHERE id = ?
    """, [category, transaction_id])
    conn.close()