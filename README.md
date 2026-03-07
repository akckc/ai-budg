# Budget-AI

A personal finance dashboard that tells you, at any moment, how much money you can safely spend — without requiring perfect bookkeeping.

> **Safe-to-Spend** = Current balance − upcoming bills + upcoming income (14-day window)

---

## What it does

| Feature | Description |
|---|---|
| **Dashboard** | Balance, monthly income/expenses, spending by category, 14-day burndown chart |
| **Safe-to-Spend** | Cash-flow forecast through your next paycheck |
| **CSV import** | Upload a bank export; duplicates are automatically skipped |
| **Manual transactions** | Add income or spending entries directly from the dashboard |
| **Category rules** | Pattern-based auto-categorization (e.g. "STARBUCKS" → Coffee) |
| **Budgets** | Set a monthly budget per category and see spend vs. budget |
| **Multi-account** | Track checking, savings, and credit accounts together |
| **Recurring events** | Store bills and income as templates; forecast includes them automatically |

---

## Quick start

### Option A — run locally with Python

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create the data directory (first run only)
mkdir -p data

# 3. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000

# 4. Open the dashboard
open http://localhost:8000
```

### Option B — run with Docker

```bash
docker build -t budget-ai .
docker run -p 8000:8000 -v $(pwd)/data:/app/data budget-ai
```

Then open **http://localhost:8000** in your browser.

---

## First-time workflow

If you've never used the app before, here's the recommended order:

1. **Open the dashboard** — `http://localhost:8000`  
   You'll see zeroed-out cards; that's expected with an empty ledger.

2. **Import your transactions** — go to `http://localhost:8000/upload`  
   Upload a CSV file exported from your bank. The expected columns are:

   ```
   Date, Description, Amount, Balance
   ```

   Optional columns: `Category`, `Source`, `Account Name`  
   Dates must be in `MM/DD/YYYY` or `YYYY-MM-DD` format.  
   Re-uploading the same file is safe — duplicates are silently skipped.

3. **Select an account** — the upload form shows a dropdown of existing accounts.  
   Choose one or type a new name to create it on the fly.

4. **Add a manual transaction** — use the "Add Transaction" card on the dashboard  
   for anything not in your CSV (cash, peer-to-peer payments, etc.).

5. **Set up category rules** — `POST /rules/add`  
   Rules auto-tag future imports so you don't have to categorize manually.

6. **Set budgets** — `POST /budgets/category`  
   Advisory only; budgets never affect your Safe-to-Spend number.

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/dashboard` | Main dashboard UI |
| `GET` | `/upload` | CSV upload form |
| `POST` | `/upload` | Process a CSV file |
| `GET` | `/transactions` | List transactions (supports `start_date`, `end_date`, `category`, `account_id` filters) |
| `POST` | `/transactions/manual` | Add a transaction (JSON or form-encoded) |
| `PUT` | `/transactions/{id}/category` | Update a transaction's category |
| `POST` | `/transactions/reclassify` | Re-apply category rules to all transactions |
| `GET` | `/forecast` | 14-day cash-flow forecast JSON |
| `GET` | `/rules/list` | List category rules |
| `POST` | `/rules/add` | Create a category rule |
| `POST` | `/budgets/category` | Set a monthly budget for a category |
| `GET` | `/budgets/summary` | Spend vs. budget for current month |
| `GET` | `/ingestion/history` | CSV import audit trail |

Interactive docs are available at **http://localhost:8000/docs** (Swagger UI).

### Adding a transaction via JSON

```bash
curl -X POST http://localhost:8000/transactions/manual \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "Checking",
    "date": "2024-01-15",
    "description": "Grocery run",
    "amount": -64.32
  }'
```

### Adding a transaction via form (e.g. from a script)

```bash
curl -X POST http://localhost:8000/transactions/manual \
  -d "account_name=Checking&date=2024-01-15&description=Grocery+run&amount=-64.32"
```

---

## CSV format reference

| Column | Required | Notes |
|---|---|---|
| `Date` | ✅ | `YYYY-MM-DD` or `MM/DD/YYYY` |
| `Description` | ✅ | Free text |
| `Amount` | ✅ | Negative = expense, positive = income |
| `Balance` | ✅ | Account balance after transaction |
| `Category` | optional | Overrides auto-categorization if present |
| `Source` | optional | Defaults to `unknown` |
| `Account Name` | optional | Assigns to named account; defaults to account selected on upload form |

---

## Project structure

```
ai-budg/
├── main.py                  # FastAPI app + router registration
├── db.py                    # DB connection + schema init
├── routes/                  # Thin HTTP handlers (no business logic)
│   ├── dashboard.py
│   ├── transactions.py
│   ├── upload.py
│   ├── rules.py
│   ├── forecast.py
│   ├── budgets.py
│   └── ingestion.py
├── services/                # Business logic
│   ├── transaction_service.py
│   ├── csv_ingest_service.py
│   ├── forecast_service.py
│   ├── budget_service.py
│   └── category_rule_engine.py
├── repositories/            # Database access only
│   ├── transactions_repository.py
│   ├── accounts_repository.py
│   └── ...
├── templates/
│   └── dashboard.html       # Dashboard UI (Jinja2)
├── data/                    # DuckDB database file (git-ignored)
│   └── budget.duckdb
└── docs/                    # Design authority, sprint history, style guide
```

---
## Requirements

- **Python 3.11+** (the codebase uses Python 3.10+ typing syntax like `str | None` and `list[...]`)

---

## Contributing

This project uses a sprint proposal workflow. Before making changes:

1. Read [`docs/design_authority.md`](docs/design_authority.md) — it defines what can and cannot change.
2. Use [`docs/sprint_proposal_template.md`](docs/sprint_proposal_template.md) to propose a change.
3. All writes must go through the **service layer** — no direct DB access in routes.
4. The forecast engine is read-only and deterministic; changes require explicit DA review.

The Tier 0 checklist (from the DA) must pass before any sprint is marked complete:

- [ ] Add transaction (manual)
- [ ] Edit transaction
- [ ] Delete transaction
- [ ] Import CSV
- [ ] Reconcile imported transactions
- [ ] Verify Safe-to-Spend calculation
- [ ] Forecast includes recurring items correctly
