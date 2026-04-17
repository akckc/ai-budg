from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
import re
import uuid


def set_transaction_recurring_link(*, transaction_id: int, recurring_event_id: int | None) -> None:
    """Update transactions.recurring_event_id for the given transaction id."""
    from db import get_db
    conn = get_db()
    try:
        conn.execute(
            "UPDATE transactions SET recurring_event_id = ? WHERE id = ?",
            [recurring_event_id, transaction_id],
        )
    finally:
        conn.close()


def _find_matching_recurring_event(conn, amount: float, tx_date) -> Optional[int]:
    """
    Find a consumable recurring event matching the given amount and date.

    Matches by:
    - amount: ≤2% variance against event amount
    - date: tx_date falls within ±5 days of an expected occurrence

    Returns the event id if found, else None.
    """
    from services.forecast_service import get_occurrences_in_window

    if isinstance(tx_date, str):
        tx_date = datetime.strptime(tx_date, '%Y-%m-%d').date()

    rows = conn.execute("""
        SELECT id, amount, frequency, day_of_month, anchor_date
        FROM recurring_events
        WHERE active = TRUE AND (allow_consume = TRUE OR allow_consume IS NULL)
    """).fetchall()

    window_start = tx_date - timedelta(days=5)

    for row in rows:
        event_id, event_amount, frequency, day_of_month, anchor_date = row

        # Amount check: ≤2% variance
        ref = max(abs(float(amount)), abs(float(event_amount)))
        if ref == 0:
            amount_match = float(amount) == float(event_amount)
        else:
            amount_match = abs(float(amount) - float(event_amount)) / ref <= 0.02

        if not amount_match:
            continue

        # Date check: any occurrence within ±5 days of tx_date
        event_dict = {
            'frequency': frequency,
            'day_of_month': day_of_month,
            'anchor_date': anchor_date,
            'amount': float(event_amount),
        }
        occurrences = get_occurrences_in_window(event_dict, window_start, window_days=10)
        for occ in occurrences:
            if abs((tx_date - occ).days) <= 5:
                return int(event_id)

    return None


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase and strip all non-alphanumeric characters."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def _get_manual_description(manual_entry: dict) -> str:
    """
    Return the best description text for a manual entry to use in matching.
    Prefers merchant_normalized (already cleaned) over raw description.
    """
    merchant = manual_entry.get('merchant') or ''
    description = manual_entry.get('description') or ''
    return merchant if merchant else description


def score_match(csv_row: dict, manual_entry: dict) -> float:
    """
    Calculate fuzzy match confidence score (0-100) between a CSV row and a manual entry.

    Inputs:
    - csv_row: dict with keys 'date' (YYYY-MM-DD), 'amount' (float), 'description' (str)
    - manual_entry: dict with keys 'date' (YYYY-MM-DD), 'amount' (float),
                    'description' (str), 'merchant' (str, optional)

    Returns:
    - score: float 0-100 representing confidence percentage

    Scoring weights:
    - Amount match (≤2% variance): 40 points
    - Date match (gradual decay):  up to 30 points, 0 at ≥7 days
    - Description similarity:      30 points

    Hard cap: if date distance > 7 days, total score cannot exceed 60.
    This prevents recurring transactions (e.g. same-amount paychecks) from
    scoring into the review or auto-match bands.

    Deterministic: Same inputs always produce same score.
    No side effects.
    """
    score = 0.0

    # --- Date scoring (weight 30): linear decay from 30 pts (0 days) to 0 pts (7 days) ---
    try:
        csv_date = datetime.strptime(csv_row['date'], '%Y-%m-%d').date()
        manual_date = datetime.strptime(manual_entry['date'], '%Y-%m-%d').date()
    except (ValueError, KeyError):
        return 0.0  # Invalid date format

    date_diff = abs((csv_date - manual_date).days)
    date_score = max(0.0, 30.0 * (1.0 - date_diff / 7.0))
    score += date_score

    # --- Amount scoring (weight 40): ≤2% variance = full 40 points ---
    try:
        csv_amount = float(csv_row['amount'])
        manual_amount = float(manual_entry['amount'])
    except (ValueError, KeyError):
        return 0.0  # Invalid amount

    ref_amount = max(abs(csv_amount), abs(manual_amount))
    if ref_amount == 0:
        # Both zero: exact match
        score += 40.0
    else:
        # Use the larger absolute value as denominator so variance is always ≤100%.
        # Amounts with very different magnitudes will have high variance and won't match.
        amount_variance = abs(csv_amount - manual_amount) / ref_amount
        if amount_variance <= 0.02:
            # ≤2% variance: full points
            score += 40.0
        elif amount_variance <= 0.05:
            # ≤5% variance: partial points
            score += 20.0
        # else: 0 points for amounts with >5% variance

    # --- Description similarity (weight 30) ---
    # For manual entries, prefer merchant_normalized (already cleaned) over raw description.
    # For CSV rows, use the description field (bank descriptions are verbose but contain
    # the merchant name).
    csv_text = _normalize_text(str(csv_row.get('description', '') or ''))
    manual_text = _normalize_text(_get_manual_description(manual_entry))

    if csv_text and manual_text:
        # Substring containment: covers short merchant names embedded in long bank strings
        # (e.g. "hyvee" found inside "pointofsalewithdrawalhyveekansascity...")
        if manual_text in csv_text or csv_text in manual_text:
            score += 30.0
        else:
            # Sequence similarity fallback for descriptions of similar length
            ratio = SequenceMatcher(None, csv_text, manual_text).ratio()
            score += ratio * 30.0

    # Hard cap: dates more than 7 days apart cannot score above 60
    if date_diff > 7:
        return min(score, 60.0)

    return min(score, 100.0)  # Cap at 100%


def get_unreconciled_manual_entries(conn, account_id: int) -> List[dict]:
    """
    Query all manual transactions for an account that haven't been reconciled yet.
    
    Returns list of dicts with keys: id, date, amount, description, merchant_normalized
    """
    query = """
    SELECT id, date, amount, description, merchant_normalized, category
    FROM transactions
    WHERE account_id = ?
      AND source = 'manual'
      AND (reconciliation_status = 'pending' OR reconciliation_status IS NULL)
    ORDER BY date DESC
    """
    rows = conn.execute(query, [account_id]).fetchall()
    
    return [
        {
            'id': r[0],
            'date': str(r[1]),
            'amount': r[2],
            'description': r[3],
            'merchant': r[4] or r[3],  # fallback to description if no merchant
            'category': r[5],
        }
        for r in rows
    ]


def get_all_entries(conn, account_id: int) -> List[dict]:
    """
    Query ALL transactions (manual + CSV + others) for an account, regardless of
    reconciliation status. Used to detect duplicates when importing new CSV data,
    including transactions from prior CSV imports that may already be reconciled.

    Returns list of dicts with keys: id, date, amount, description, merchant, category, source
    """
    query = """
    SELECT id, date, amount, description, merchant_normalized, category, source
    FROM transactions
    WHERE account_id = ?
    ORDER BY date DESC
    """
    rows = conn.execute(query, [account_id]).fetchall()

    return [
        {
            'id': r[0],
            'date': str(r[1]),
            'amount': r[2],
            'description': r[3],
            'merchant': r[4] or r[3],  # fallback to description if no merchant
            'category': r[5],
            'source': r[6],
        }
        for r in rows
    ]


def reconcile_csv_with_manual(conn, account_id: int, csv_rows: List[dict]) -> dict:
    """
    Match CSV rows against ALL existing transactions using fuzzy matching.

    Checks for duplicates against manual entries, prior CSV imports, and any other
    existing transactions to prevent duplicate insertions.

    Inputs:
    - conn: Database connection
    - account_id: User's account ID
    - csv_rows: List of dicts with 'date', 'amount', 'merchant', 'description'

    Returns:
    - result: dict with keys:
      * 'auto_matched': list of (csv_idx, existing_id, score) tuples (score >=90%)
      * 'review_matches': list of (csv_idx, existing_id, score) tuples (70-89%)
      * 'unmatched_csv': list of csv_idx values
      * 'unmatched_manual': list of manual entry IDs not matched (for finalization)
      * 'session_id': unique ID for this reconciliation session
      * 'csv_rows': original CSV data for later use
      * 'existing_entries': all existing transactions used for matching

    Deterministic: Same inputs always produce same output.
    No side effects on DB; only reads.
    """
    session_id = str(uuid.uuid4())

    # Query ALL existing transactions (not just manual!)
    existing_entries = get_all_entries(conn, account_id)

    auto_matched = []
    review_matches = []
    matched_csv_indices = set()
    matched_existing_ids = set()

    # For each CSV row, find best match against ALL existing transactions
    for csv_idx, csv_row in enumerate(csv_rows):
        best_score = 0.0
        best_existing_id = None

        for existing_entry in existing_entries:
            if existing_entry['id'] in matched_existing_ids:
                # Already matched to another CSV row
                continue

            score = score_match(csv_row, existing_entry)

            if score > best_score:
                best_score = score
                best_existing_id = existing_entry['id']

        # Classify based on confidence threshold
        if best_score >= 90.0:
            auto_matched.append((csv_idx, best_existing_id, best_score))
            matched_csv_indices.add(csv_idx)
            matched_existing_ids.add(best_existing_id)
        elif best_score >= 70.0:
            review_matches.append((csv_idx, best_existing_id, best_score))
            matched_csv_indices.add(csv_idx)
            matched_existing_ids.add(best_existing_id)
        # else: unmatched CSV row (new transaction to insert)

    # Identify unmatched CSV rows
    unmatched_csv = [i for i in range(len(csv_rows)) if i not in matched_csv_indices]

    # Only mark manual entries as unmatched (not prior CSV imports)
    unmatched_manual = [
        e['id'] for e in existing_entries
        if e['id'] not in matched_existing_ids and e.get('source') == 'manual'
    ]

    return {
        'auto_matched': auto_matched,
        'review_matches': review_matches,
        'unmatched_csv': unmatched_csv,
        'unmatched_manual': unmatched_manual,
        'session_id': session_id,
        'csv_rows': csv_rows,  # Store for finalization
        'existing_entries': existing_entries,  # All entries used for matching and display
    }


def finalize_reconciliation(conn, account_id: int, reconciliation_data: dict, approvals: dict) -> dict:
    """
    Apply approved matches to DB, insert unmatched CSV rows, and update reconciliation status.
    
    Inputs:
    - conn: Database connection
    - account_id: User's account ID
    - reconciliation_data: Original reconciliation result from reconcile_csv_with_manual
    - approvals: dict with keys:
      * 'approved_indices': list of (csv_idx, manual_id) tuples to apply
      * 'add_as_new_indices': list of csv_idx values the user wants inserted as new transactions
        (review-match rows where the user chose "Add as New" instead of "Confirm Match")
    
    Operations:
    - For each approved match: UPDATE transactions with CSV data, mark as matched
    - For unmatched CSV rows: INSERT as new transactions
    - For unmatched manual entries: UPDATE reconciliation_status='unmatched'
    
    Returns:
    - result: dict with keys:
      * 'matched_count': int
      * 'inserted_count': int
      * 'status': 'success' or 'error'
    
    Deterministic writes: Each call is atomic and idempotent for same session_id.
    """
    matched_count = 0
    inserted_count = 0
    
    try:
        csv_rows = reconciliation_data['csv_rows']
        approved_set = set(approvals.get('approved_indices', []))
        add_as_new_set = set(approvals.get('add_as_new_indices', []))

        # Build a lookup map of existing entries for source-aware matching
        existing_entries = reconciliation_data.get('existing_entries', reconciliation_data.get('manual_entries', []))
        existing_entries_map = {e['id']: e for e in existing_entries}

        # Apply approved matches
        for csv_idx, existing_id in approved_set:
            csv_row = csv_rows[csv_idx]
            existing_entry = existing_entries_map.get(existing_id, {})

            if existing_entry.get('source') == 'manual':
                # Manual entry: update with authoritative CSV data
                conn.execute("""
                UPDATE transactions
                SET source = 'csv',
                    source_id = ?,
                    reconciliation_status = 'matched',
                    amount = ?,
                    description = ?,
                    date = ?,
                    balance = ?
                WHERE id = ?
                """, [
                    reconciliation_data['session_id'],
                    csv_row.get('amount'),
                    csv_row.get('description'),
                    csv_row.get('date'),
                    csv_row.get('balance'),
                    existing_id
                ])
                # Tag with recurring_event_id if a matching event is found
                rec_event_id = _find_matching_recurring_event(
                    conn, csv_row.get('amount'), csv_row.get('date')
                )
            else:
                # Existing CSV (or other) entry: just mark as matched, preserve original data
                conn.execute("""
                UPDATE transactions
                SET reconciliation_status = 'matched',
                    source_id = ?
                WHERE id = ?
                """, [
                    reconciliation_data['session_id'],
                    existing_id
                ])
                rec_event_id = _find_matching_recurring_event(
                    conn, existing_entry.get('amount'), existing_entry.get('date')
                )

            if rec_event_id is not None:
                conn.execute(
                    "UPDATE transactions SET recurring_event_id = ? WHERE id = ?",
                    [rec_event_id, existing_id]
                )
            matched_count += 1
        
        # Insert unmatched CSV rows and any review-match rows the user chose "Add as New"
        matched_csv_indices = {idx for idx, _ in approved_set}
        indices_to_insert = set(reconciliation_data['unmatched_csv']) | add_as_new_set
        for csv_idx in indices_to_insert:
            if csv_idx in matched_csv_indices:
                continue  # Skip if user approved a match for this row
            
            csv_row = csv_rows[csv_idx]

            # Check if transaction already exists (duplicate detection)
            existing = conn.execute("""
            SELECT id FROM transactions
            WHERE account_id = ? AND date = ? AND description = ? AND amount = ?
            """, [
                account_id,
                csv_row.get('date'),
                csv_row.get('description'),
                csv_row.get('amount')
            ]).fetchone()

            if existing:
                # Duplicate found, skip it silently
                continue

            new_row = conn.execute("""
            INSERT INTO transactions
            (account_id, date, description, amount, balance, category, source, source_id, reconciliation_status)
            VALUES (?, ?, ?, ?, ?, ?, 'csv', ?, 'matched')
            RETURNING id
            """, [
                account_id,
                csv_row.get('date'),
                csv_row.get('description'),
                csv_row.get('amount'),
                csv_row.get('balance'),
                csv_row.get('category'),
                reconciliation_data['session_id']
            ]).fetchone()
            inserted_count += 1

            # Tag with recurring_event_id if a matching event is found
            if new_row:
                rec_event_id = _find_matching_recurring_event(
                    conn, csv_row.get('amount'), csv_row.get('date')
                )
                if rec_event_id is not None:
                    conn.execute(
                        "UPDATE transactions SET recurring_event_id = ? WHERE id = ?",
                        [rec_event_id, new_row[0]]
                    )
        
        # Mark unmatched manual entries
        matched_manual_ids = {mid for _, mid in approved_set}
        for manual_id in reconciliation_data['unmatched_manual']:
            if manual_id in matched_manual_ids:
                continue  # Skip if user manually approved a match
            
            conn.execute("""
            UPDATE transactions
            SET reconciliation_status = 'unmatched'
            WHERE id = ?
            """, [manual_id])
        
        return {
            'matched_count': matched_count,
            'inserted_count': inserted_count,
            'status': 'success'
        }
    
    except Exception as e:
        return {
            'matched_count': 0,
            'inserted_count': 0,
            'status': 'error',
            'error': str(e)
        }
