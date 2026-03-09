from db import get_db
from repositories.transaction_reconciliation_repository import (
    reconcile_csv_with_manual,
    finalize_reconciliation
)


def initiate_reconciliation(account_id: int, csv_rows: list) -> dict:
    """
    Orchestrate the reconciliation workflow: match CSV against manual entries.
    
    Inputs:
    - account_id: User's account ID
    - csv_rows: Parsed CSV data as list of dicts
    
    Returns:
    - reconciliation_data: dict with matches, session_id, and original data
    
    Deterministic: No side effects; only reads from DB.
    """
    conn = get_db()
    try:
        result = reconcile_csv_with_manual(conn, account_id, csv_rows)
        return result
    finally:
        conn.close()


def apply_reconciliation(account_id: int, reconciliation_data: dict, user_approvals: dict) -> dict:
    """
    Apply user-approved matches and finalize reconciliation.
    
    Inputs:
    - account_id: User's account ID
    - reconciliation_data: Original reconciliation result
    - user_approvals: dict with 'approved_indices' list of (csv_idx, manual_id) tuples
    
    Returns:
    - result: dict with matched_count, inserted_count, status
    
    Deterministic writes: Updates/inserts based on approved matches only.
    """
    conn = get_db()
    try:
        result = finalize_reconciliation(conn, account_id, reconciliation_data, user_approvals)
        return result
    finally:
        conn.close()
