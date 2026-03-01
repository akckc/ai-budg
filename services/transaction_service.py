from db import get_db
from repositories.transactions_repository import (
    get_all_transactions as repo_get_all_transactions,
    update_category as repo_update_category,
    insert_transaction as repo_insert_transaction,
    get_transaction_by_id as repo_get_transaction_by_id,
)
from repositories.category_rules_repository import get_all_category_rules
from services.category_rule_engine import evaluate_category


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
    be set (``account_name`` defaults to ``"Primary Account"``).

    If no category is provided, deterministically evaluates rules.
    """
    conn = get_db()
    try:
        # If no category provided, try to apply rules
        if category is None:
            rules = get_all_category_rules(conn)
            category = evaluate_category(description, rules)

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


def apply_category_rules_to_transaction(transaction_id):
    """Fetch a transaction, evaluate rules against description, update category.

    Pure function of transaction.description + sorted rules.
    Applies deterministically; no impact to balance, amount, or date.
    """
    conn = get_db()
    try:
        # Fetch transaction
        tx = repo_get_transaction_by_id(conn, transaction_id)
        if not tx:
            return

        # Extract description
        description = tx[3]  # description is at index 3 in the SELECT result

        # Fetch rules and evaluate
        rules = get_all_category_rules(conn)
        matched_category = evaluate_category(description, rules)

        # Update if match found
        if matched_category:
            repo_update_category(conn, transaction_id, matched_category)
    finally:
        conn.close()


def reclassify_all_transactions():
    """Re-apply category rules to all transactions deterministically.

    Fetches all transactions, evaluates each against rules in priority order,
    and updates category if a rule matches.

    Returns count of transactions updated.
    """
    conn = get_db()
    try:
        # Fetch all transactions
        transactions = repo_get_all_transactions(conn)

        # Fetch rules once (sorted by priority)
        rules = get_all_category_rules(conn)

        updated_count = 0
        for tx in transactions:
            transaction_id = tx[0]
            description = tx[3]

            # Deterministically evaluate
            matched_category = evaluate_category(description, rules)

            # Update if match found
            if matched_category:
                repo_update_category(conn, transaction_id, matched_category)
                updated_count += 1

        return updated_count
    finally:
        conn.close()
