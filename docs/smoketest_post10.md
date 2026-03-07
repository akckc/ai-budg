# Smoke Test (Master) — API + UI Regression Checklist

**Purpose:** A repeatable smoke/regression script to run after each sprint/PR to ensure core workflows still function.

**Default base URL:** `http://localhost:8347`

**Recommended cadence:** run this after any change touching ingestion, schema, categorization, budgets, or forecast.

---

## 0) Preconditions
- API is running locally.
- You have at least one CSV available to upload.
- You know whether this sprint required a DB rebuild/migration.

Optional environment hint:
- If you're on Unraid/Docker, you may also want:
  - `docker logs -f <container-name>`

---

## 1) Sanity: Root + Dashboard Loads
### 1.1 Root redirects to dashboard
```bash
curl -i http://localhost:8347/ | head -n 20
```

**Pass:** 30x redirect to `/dashboard` (or dashboard content).

### 1.2 Dashboard renders HTML
```bash
curl -i http://localhost:8347/dashboard | head -n 20
```

**Pass:** `200 OK` and `Content-Type: text/html` (or HTML body).

---

## 2) Forecast Endpoint Regression (Deterministic / Read-only)
### 2.1 Forecast returns JSON
```bash
curl -s http://localhost:8347/forecast | head -c 2000; echo
```

**Pass:** JSON object with timeline fields (no `error`).

### 2.2 Forecast determinism spot-check (no intervening writes)
```bash
curl -s http://localhost:8347/forecast > /tmp/forecast1.json
curl -s http://localhost:8347/forecast > /tmp/forecast2.json
diff /tmp/forecast1.json /tmp/forecast2.json || true
```

**Pass:** no diff (or only expected ordering/formatting differences; ideally identical).

### 2.3 Optional: as_of_date parameter works
```bash
curl -s "http://localhost:8347/forecast?as_of_date=2026-03-05" | head -c 2000; echo
```

**Pass:** JSON returned, no error.

---

## 3) Transactions: Read Regression
### 3.1 List all transactions
```bash
curl -s http://localhost:8347/transactions | head -c 4000; echo
```

**Pass:** JSON with `transactions` array.

### 3.2 Filtered transactions (date range)
```bash
curl -s "http://localhost:8347/transactions?start_date=2026-03-01&end_date=2026-03-31" | head -c 4000; echo
```

**Pass:** JSON with `transactions` array.

---

## 4) Manual Transaction Entry Regression
### 4.1 Add a manual transaction (form-style payload)
```bash
curl -s -X POST http://localhost:8347/transactions/manual \
  -d "date=2026-03-05&description=SMOKE+TEST+-+MANUAL+TX&amount=-1.23&category=Test" \
  -H "Content-Type: application/x-www-form-urlencoded"
echo
```

**Pass:** redirects back to `/dashboard` (status 303) or returns `{"success": true}`.

### 4.2 Confirm it appears in /transactions
```bash
curl -s http://localhost:8347/transactions | head -c 4000; echo
```

**Pass:** the new transaction is present.

---

## 5) Category Rules UI + API Regression
### 5.1 Rules page returns HTML
```bash
curl -i http://localhost:8347/rules | head -n 20
```

**Pass:** `200 OK` and HTML.

### 5.2 List rules
```bash
curl -s http://localhost:8347/rules/list | head -c 2000; echo
```

**Pass:** JSON with `count` and `rules`.

### 5.3 Add a rule
```bash
curl -s -X POST http://localhost:8347/rules/add \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "SMOKE TEST MERCHANT",
    "category": "Test",
    "min_amount": null,
    "max_amount": null
  }'
echo
```

**Pass:** status ok / rule added.

---

## 6) CSV Upload + Account Selection Regression (#8, #9)
### 6.1 Upload page loads with account dropdown
```bash
curl -s http://localhost:8347/upload | grep -c "account"
```

**Pass:** returns > 0 (dropdown exists).

### 6.2 Upload a CSV with account selection
```bash
curl -s -X POST http://localhost:8347/upload \
  -F "file=@/path/to/your.csv" \
  -F "account_id=1"
```

**Pass:** HTML response page (success or error) with row count, not JSON redirect.

### 6.3 Upload result page shows success (green box)
```bash
curl -s -X POST http://localhost:8347/upload \
  -F "file=@/path/to/your.csv" \
  -F "account_id=1" | grep -i "success\|imported"
```

**Pass:** contains success or row count message.

---

## 7) Ingestion Transparency Regression
### 7.1 Ingestion history
```bash
curl -s http://localhost:8347/ingestion/history | head -c 4000; echo
```

**Pass:** JSON array/object of ingestion events (no error).

---

## 8) Budgets Regression (API)
### 8.1 Create/update a category budget
```bash
curl -s -X POST http://localhost:8347/budgets/category \
  -H "Content-Type: application/json" \
  -d '{
    "category_name": "Groceries",
    "monthly_budget": 400,
    "active": true
  }'
echo
```

**Pass:** `{"status":"ok"}` (or equivalent).

### 8.2 Budget summary endpoint
```bash
curl -s http://localhost:8347/budgets/summary; echo
```

**Pass:** JSON response (may be `[]` if no budgets/spend recognized, but should not 500).

### 8.3 Spend-vs-budget summary endpoint
```bash
curl -s http://localhost:8347/spend-vs-budget | head -c 4000; echo
```

**Pass:** JSON response (no error).

---

## 9) Sprint-Specific Checks
Add one section per sprint and keep them forever.

### Cleanup Sprint — JSON API + Account Selection + Upload Success Pages (#8, #9, #19)

#### 9.1 JSON payload for /transactions/manual (NEW in #19)
```bash
curl -s -X POST http://localhost:8347/transactions/manual \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-03-05",
    "description": "SMOKE TEST JSON",
    "amount": -2.50,
    "category": "Test",
    "account_name": "Checking"
  }'
echo
```

**Pass:** `{"success": true, "message": "Transaction added"}` (JSON response, not redirect).

#### 9.2 Form-style still works (backwards compatible)
```bash
curl -s -X POST http://localhost:8347/transactions/manual \
  -d "date=2026-03-05&description=SMOKE+TEST+FORM&amount=-2.50&category=Test" \
  -H "Content-Type: application/x-www-form-urlencoded"
echo
```

**Pass:** redirects to `/dashboard` (303) or `{"success": true}`.

#### 9.3 Upload form shows account dropdown (#8)
```bash
curl -s http://localhost:8347/upload | grep "accountSelect"
```

**Pass:** contains account select element.

#### 9.4 Upload shows success page with row count (#9)
```bash
curl -s -X POST http://localhost:8347/upload \
  -F "file=@/path/to/your.csv" \
  -F "account_id=1" | grep -i "imported\|success"
```

**Pass:** HTML page with success message and row count (not JSON).

---

## 10) Quick Failure Triage
If something fails:
1. Check container logs (if Docker):
   - `docker logs --tail 200 <container-name>`
2. Identify endpoint + HTTP status code.
3. Re-run with headers:
   - `curl -i <url>`
4. Record failure + stack trace snippet in the PR description / issue.

---
