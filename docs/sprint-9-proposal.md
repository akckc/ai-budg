# ============================================
# Budget-AI — Sprint 9 Proposal
# DA Version: 1.1
# ============================================

## Sprint Name
Ingestion Transparency + Transaction Filtering

---

## DA Section Impacted

- Tier 1 – Core Experience
- System Invariants – Ledger Authority
- Architecture Principles – Thin Routes / Service Layer Enforcement

---

## Change Summary (3–6 bullets max)

- Add ingestion run tracking for CSV imports
- Expose read-only endpoint to view ingestion history (timestamp, inserted count, skipped count)
- Add transaction filtering by date range, category, and account
- Preserve deterministic ingestion and ledger authority
- Ensure no impact to forecast, Safe-to-Spend, or reconciliation logic

---

## Layer Impact

### Routes
- Add `GET /transactions` with optional filters (start_date, end_date, category, account_id)
- Add `GET /ingestion/history` to view ingestion run metadata
- No business logic in routes

### Services
- Implement `get_filtered_transactions()` in transaction_service
- Implement `get_ingestion_history()` in ingestion_service
- Both return deterministic, query-based results

### Repositories
- Add `ingestion_runs` CRUD in new ingestion_repository
- Extend transaction_repository with `get_transactions_filtered()` method
- New table: `ingestion_runs`

### Schema
- **New Table: ingestion_runs**
  ```sql
  CREATE TABLE IF NOT EXISTS ingestion_runs (
      id BIGINT PRIMARY KEY DEFAULT nextval('ingestion_runs_id_seq'),
      filename VARCHAR NOT NULL,
      inserted_count INTEGER NOT NULL,
      skipped_count INTEGER NOT NULL,
      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
