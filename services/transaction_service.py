from db import get_db
from repositories.transactions_repository import (
    get_all_transactions as repo_get_all_transactions,
    update_category as repo_update_category,
    insert_transaction as repo_insert_transaction,
)


def get_all_transactions(account_name=None, limit=None):
    """Return transactions, optionally filtering by account.

    Opens and closes a database connection on the caller’s behalf.
    """
    conn = get_db()
    try:
        return repo_get_all_transactions(conn, account_name=account_name, limit=limit)
    finally:
        conn.close()


def update_transaction_category(transaction_id, category):
    conn = get_db()
    try:
        repo_update_category(conn, transaction_id, category)
    finally:
        conn.close()


def add_transaction(*, date, description, amount,
                    balance=None, category=None, source='Manual',
                    user_id=None, merchant_id=None,
                    account_id=None, account_name=None):
    """Service wrapper around repository insert.

    Accepts either ``account_id`` or ``account_name``; one of them must
    be set (``account_name`` defaults to ``\"Primary Account\"``).
    """
    conn = get_db()
    try:
        return repo_insert_transaction(
            conn,
            date=date,
            description=description,
            amount=amount,
            balance=balance,
            category=category,
            source=source,
            user_id=user_id,
            merchant_id=merchant_id,
            account_id=account_id,
            account_name=account_name,
        )
    finally:
        conn.close()
