# Sprint Proposal

## Sprint Name
Bank Reconciliation with Fuzzy Matching

## DA Reference
**Design Authority v1.1 — Three-Layer Architecture**
- **Section 2.1**: Routes are thin presentation wrappers; no business logic
- **Section 2.2**: Services orchestrate workflow, coordinate repositories, manage connections
- **Section 2.3**: Repositories own all database operations and data access logic
- **Section 3.1**: Deterministic operations - fuzzy matching scoring is reproducible from same inputs
- **Section 4.2**: CSV as authoritative source when user approves matches

## Change Summary
Implements automated bank reconciliation with fuzzy matching algorithm to reconcile CSV bank statement uploads with existing manual transaction entries. The system:

1. **Fuzzy Matching Engine**: Uses deterministic 100-point scoring system
   - Date match ±1 day: 30 points
   - Amount match ±$0.50: 30 points (graduated: exact ≤$0.01, close ≤$0.25, acceptable ≤$0.50)
   - Merchant normalized match: 40 points (exact match), 20 points (partial substring match)

2. **Confidence Tiers & Workflow**:
   - ≥90%: Auto-approved matches (pre-checked in review UI)
   - 70-89%: Requires user review (unchecked by default)
   - <70%: No match (unmatched)

3. **User Review Process**:
   - After CSV upload, redirect to `/reconciliation/review` page
   - Display 4 sections: Auto-matched, Review Matches, Unmatched CSV, Unmatched Manual
   - User approves/rejects matches via checkboxes
   - Finalization updates DB: CSV data supersedes manual entries, inserts new transactions, marks unmatched

4. **Audit Trail**: New columns track reconciliation metadata
   - `source`: 'manual' or 'csv'
   - `source_id`: Reconciliation session ID
   - `reconciliation_status`: 'pending', 'matched', 'unmatched'

## Files Affected

### Modified Files
- **db.py**: Added 3 columns to transactions table (source, source_id, reconciliation_status) + backfill query
- **routes/upload.py**: Integrated reconciliation workflow, added CSV parsing helper, redirect to review page
- **main.py**: Registered reconciliation router

### New Files Created
- **repositories/transaction_reconciliation_repository.py** (306 lines)
  - `score_match()`: Fuzzy matching algorithm implementation
  - `get_unreconciled_manual_entries()`: Query pending manual transactions
  - `reconcile_csv_with_manual()`: Main matching function
  - `finalize_reconciliation()`: Apply approved matches, insert/update transactions

- **services/reconciliation_service.py** (48 lines)
  - `initiate_reconciliation()`: Orchestrates matching workflow
  - `apply_reconciliation()`: Orchestrates finalization
  - Thin service layer - opens/closes DB connections, calls repository

- **routes/reconciliation.py** (206 lines)
  - GET `/reconciliation/review`: Renders review page with match data
  - POST `/reconciliation/finalize`: Processes user approvals, applies matches
  - In-memory session storage (production note: upgrade to Redis/DB)

- **templates/reconciliation_review.html** (381 lines)
  - Dark theme UI matching dashboard/transactions
  - Interactive checkboxes for approval/rejection
  - JavaScript to collect approvals as JSON array
  - Four sections: Auto-matched, Review, Unmatched CSV, Unmatched Manual

## Service Layer Compliance

**Strict DA v1.1 Compliance**:

1. **Routes Layer** (routes/reconciliation.py, routes/upload.py):
   - Thin presentation wrappers only
   - No database access, no business logic
   - Calls service functions, renders templates
   - HTTP request/response handling only

2. **Services Layer** (services/reconciliation_service.py):
   - Orchestrates workflow between repository calls
   - Manages database connection lifecycle (open → call repo → close)
   - Zero business logic duplication
   - No direct SQL or database access

3. **Repositories Layer** (repositories/transaction_reconciliation_repository.py):
   - Owns ALL database operations (SELECT, UPDATE, INSERT)
   - Implements fuzzy matching scoring algorithm
   - Performs data transformations (merchant normalization)
   - Only layer that executes SQL

**Workflow Validation**:
- Upload route parses CSV → calls service
- Service opens connection → calls repository matching function → returns results
- Route stores session → redirects to review
- User submits form → route calls service
- Service opens connection → calls repository finalization → closes connection
- No business logic in routes, no DB access in services

## Multi-Account Impact

**Account-Scoped Reconciliation**:
- Reconciliation operates per-account (account_id parameter required)
- Fuzzy matching only compares CSV rows against manual entries within same account
- Session data stored per-account
- Unmatched entries marked with account isolation
- No cross-account contamination

**Workflow**:
- User selects account on upload page (existing UI)
- Reconciliation query: `WHERE account_id = ? AND source = 'manual' AND reconciliation_status = 'pending'`
- All UPDATE/INSERT operations include account_id WHERE clause
- Each reconciliation session is account-specific

## Determinism Impact

**✓ Forecast Determinism Preserved**:

1. **Read-Only Reconciliation Metadata**: New columns are audit trail only
   - `source`, `source_id`, `reconciliation_status` NOT used in ledger/forecast calculations
   - Existing queries unaffected (columns have DEFAULT values, NULL-safe)
   
2. **Deterministic Fuzzy Matching**: Same inputs always produce same scores
   - No randomness, no timestamps in scoring algorithm
   - Normalized merchant matching is string-based (deterministic)
   - Date/amount comparisons are pure arithmetic

3. **Backward Compatible Schema**: Backfill query ensures existing transactions have consistent state
   - All existing rows set to: `source='manual'`, `reconciliation_status='matched'`
   - New manual entries default to same values
   - CSV entries explicitly marked with different source

4. **Feature Flag Available**: `USE_RECONCILIATION = True` in routes/upload.py
   - Can disable to fall back to old direct ingestion workflow
   - Preserves existing behavior when disabled

5. **No Side Effects on Existing Logic**:
   - Category assignment unaffected (uses same category_rule_engine)
   - Budget calculations unchanged
   - Forecast projections unchanged (only adds metadata, doesn't modify amounts/dates)
   - Safe-to-Spend calculations unaffected

## Tier 0 Validation Checklist

### Core Features (Unaffected)
- [x] **Manual add**: Unaffected - still uses existing add_transaction()
- [x] **Edit**: Unaffected - edit routes unchanged
- [x] **Delete**: Unaffected - delete routes unchanged
- [x] **CSV import**: Enhanced with reconciliation option (falls back to old behavior if disabled)
- [x] **Safe-to-Spend**: Unaffected - calculations don't use reconciliation columns
- [x] **Forecast includes recurring items**: Unaffected - forecast logic unchanged

### New Feature (Introduced)
- [ ] **Reconcile**: NEW FEATURE - Requires Tier 0 validation
  - Upload CSV with existing manual entries → Verify fuzzy matching fires
  - Check auto-matched (≥90%) are pre-checked
  - Check review matches (70-89%) require user action
  - Approve matches → Verify CSV data supersedes manual entry
  - Reject matches → Verify manual entry preserved, CSV inserted as new
  - Verify unmatched CSV rows inserted as new transactions
  - Verify unmatched manual entries marked `reconciliation_status='unmatched'`

## Testing Recommendations

1. **Reconciliation Workflow End-to-End**:
   - Add 5 manual transactions with known dates/amounts/merchants
   - Upload CSV with 5 matching rows (exact matches → should be 99-100% confidence)
   - Verify redirect to review page
   - Verify auto-matched section shows 5 transactions pre-checked
   - Submit form → Verify manual entries updated with CSV data
   - Check database: `SELECT source, source_id, reconciliation_status FROM transactions`

2. **Fuzzy Matching Edge Cases**:
   - Date off by 1 day: Should score ~90% if amount/merchant match
   - Amount off by $0.30: Should score ~90% if date/merchant match
   - Merchant variation (e.g., "Amazon" vs "AMAZON.COM"): Should score ~95%
   - All different: Should be unmatched (<70%)

3. **User Rejection Workflow**:
   - Uncheck an auto-matched entry → Submit
   - Verify manual entry preserved (not updated)
   - Verify CSV row inserted as NEW transaction

4. **Feature Flag Test**:
   - Set `USE_RECONCILIATION = False` in routes/upload.py
   - Upload CSV → Verify old direct ingestion workflow fires
   - Verify redirect to success page (not review page)

5. **Multi-Account Isolation**:
   - Add manual transactions to Account A
   - Upload CSV to Account B
   - Verify no matches found (different accounts)

## Production Notes

1. **Session Storage**: Currently in-memory dict (`_reconciliation_sessions`)
   - **Recommendation**: Upgrade to Redis or database table for production
   - **Impact**: Sessions lost on server restart (users must re-upload CSV)

2. **Performance**: Fuzzy matching is O(n*m) where n=CSV rows, m=manual entries
   - **Current**: Acceptable for typical user volumes (100s of transactions)
   - **Scaling**: May need optimization (indexing, caching) for thousands of transactions

3. **Merchant Normalization**: Basic lowercase + punctuation removal
   - **Enhancement**: Consider dedicated merchant normalization library for better matching

4. **Audit Trail**: Reconciliation session IDs logged in `source_id` column
   - **Recommendation**: Add reconciliation_history table for detailed audit logs

## Rollback Plan

If issues arise, rollback is safe:

1. **Disable Feature**: Set `USE_RECONCILIATION = False` in routes/upload.py
   - Immediately reverts to old direct ingestion workflow
   - No data loss, no broken functionality

2. **Schema Rollback**: New columns are nullable with defaults
   - Can drop columns if needed: `ALTER TABLE transactions DROP COLUMN source, source_id, reconciliation_status`
   - Existing queries unaffected

3. **Code Removal**: All new files are isolated
   - Remove reconciliation router from main.py
   - Delete new files: reconciliation_service.py, transaction_reconciliation_repository.py, reconciliation.py, reconciliation_review.html
