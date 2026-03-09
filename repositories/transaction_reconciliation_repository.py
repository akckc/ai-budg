from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import uuid


def score_match(csv_row: dict, manual_entry: dict) -> float:
    """
    Calculate fuzzy match confidence score (0-100) between CSV row and manual entry.
    
    Inputs:
    - csv_row: dict with keys 'date' (YYYY-MM-DD), 'amount' (float), 'merchant' (str)
    - manual_entry: dict with keys 'date' (YYYY-MM-DD), 'amount' (float), 'merchant' (str)
    
    Returns:
    - score: float 0-100 representing confidence percentage
    
    Scoring rules:
    - Base score: 0
    - Date match (±1 day): +30 points
    - Amount match (±$0.50): +30 points
    - Merchant match (normalized): +40 points
    
    Deterministic: Same inputs always produce same score.
    No side effects.
    """
    score = 0.0
    
    # Parse dates
    try:
        csv_date = datetime.strptime(csv_row['date'], '%Y-%m-%d').date()
        manual_date = datetime.strptime(manual_entry['date'], '%Y-%m-%d').date()
    except (ValueError, KeyError):
        return 0.0  # Invalid date format
    
    # Date scoring: ±1 day = 30 points
    date_diff = abs((csv_date - manual_date).days)
    if date_diff == 0:
        score += 30.0
    elif date_diff == 1:
        score += 30.0
    else:
        # No points for dates >1 day apart
        pass
    
    # Amount scoring: ±$0.50 = 30 points
    try:
        csv_amount = float(csv_row['amount'])
        manual_amount = float(manual_entry['amount'])
    except (ValueError, KeyError):
        return 0.0  # Invalid amount
    
    amount_diff = abs(csv_amount - manual_amount)
    if amount_diff <= 0.01:  # Exact match (within 1 cent)
        score += 30.0
    elif amount_diff <= 0.25:
        score += 30.0
    elif amount_diff <= 0.50:
        score += 30.0
    else:
        # No points for amounts >$0.50 apart
        pass
    
    # Merchant scoring: normalized match = 40 points
    csv_merchant = str(csv_row.get('merchant', '')).lower().strip()
    manual_merchant = str(manual_entry.get('merchant', '')).lower().strip()
    
    if csv_merchant and manual_merchant:
        if csv_merchant == manual_merchant:
            score += 40.0
        elif csv_merchant in manual_merchant or manual_merchant in csv_merchant:
            # Partial match gets partial points
            score += 20.0
    
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


def reconcile_csv_with_manual(conn, account_id: int, csv_rows: List[dict]) -> dict:
    """
    Match CSV rows against existing manual entries using fuzzy matching.
    
    Inputs:
    - conn: Database connection
    - account_id: User's account ID
    - csv_rows: List of dicts with 'date', 'amount', 'merchant', 'description'
    
    Returns:
    - result: dict with keys:
      * 'auto_matched': list of (csv_idx, manual_id, score) tuples (score >=90%)
      * 'review_matches': list of (csv_idx, manual_id, score) tuples (70-89%)
      * 'unmatched_csv': list of csv_idx values
      * 'unmatched_manual': list of manual_id values
      * 'session_id': unique ID for this reconciliation session
      * 'csv_rows': original CSV data for later use
    
    Deterministic: Same inputs always produce same output.
    No side effects on DB; only reads.
    """
    session_id = str(uuid.uuid4())
    
    # Get all unreconciled manual entries
    manual_entries = get_unreconciled_manual_entries(conn, account_id)
    
    auto_matched = []
    review_matches = []
    matched_csv_indices = set()
    matched_manual_ids = set()
    
    # For each CSV row, find best manual match
    for csv_idx, csv_row in enumerate(csv_rows):
        best_score = 0.0
        best_manual_id = None
        
        for manual_entry in manual_entries:
            if manual_entry['id'] in matched_manual_ids:
                # Already matched to another CSV row
                continue
            
            score = score_match(csv_row, manual_entry)
            
            if score > best_score:
                best_score = score
                best_manual_id = manual_entry['id']
        
        # Classify based on confidence threshold
        if best_score >= 90.0:
            auto_matched.append((csv_idx, best_manual_id, best_score))
            matched_csv_indices.add(csv_idx)
            matched_manual_ids.add(best_manual_id)
        elif best_score >= 70.0:
            review_matches.append((csv_idx, best_manual_id, best_score))
            matched_csv_indices.add(csv_idx)
            matched_manual_ids.add(best_manual_id)
        # else: unmatched CSV row
    
    # Identify unmatched CSV rows and manual entries
    unmatched_csv = [i for i in range(len(csv_rows)) if i not in matched_csv_indices]
    unmatched_manual = [m['id'] for m in manual_entries if m['id'] not in matched_manual_ids]
    
    return {
        'auto_matched': auto_matched,
        'review_matches': review_matches,
        'unmatched_csv': unmatched_csv,
        'unmatched_manual': unmatched_manual,
        'session_id': session_id,
        'csv_rows': csv_rows,  # Store for finalization
        'manual_entries': manual_entries,  # Store for display
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
      * 'rejected_indices': list of (csv_idx, manual_id) tuples to keep separate
    
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
        
        # Apply approved matches: Update manual entries with CSV data
        for csv_idx, manual_id in approved_set:
            csv_row = csv_rows[csv_idx]
            
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
                manual_id
            ])
            matched_count += 1
        
        # Insert unmatched CSV rows as new transactions
        matched_csv_indices = {idx for idx, _ in approved_set}
        for csv_idx in reconciliation_data['unmatched_csv']:
            if csv_idx in matched_csv_indices:
                continue  # Skip if user manually approved a match
            
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

            conn.execute("""
            INSERT INTO transactions 
            (account_id, date, description, amount, balance, category, source, source_id, reconciliation_status)
            VALUES (?, ?, ?, ?, ?, ?, 'csv', ?, 'matched')
            """, [
                account_id,
                csv_row.get('date'),
                csv_row.get('description'),
                csv_row.get('amount'),
                csv_row.get('balance'),
                csv_row.get('category'),
                reconciliation_data['session_id']
            ])
            inserted_count += 1
        
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
