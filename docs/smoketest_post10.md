# Smoke Test — Sprint 10: Merchant Normalization Layer

## Preconditions
- API is running locally (example: `http://localhost:8347`)
- Database is initialized / migrated for the sprint (schema includes new merchant normalization fields)
- You have at least one CSV available to upload (or you can create a manual transaction)

> If you rebuilt the DB, run a fresh CSV upload before validating merchant normalization.

---

## 1) Health / Core Pages Still Load
1. Open dashboard in browser:
   - `GET /dashboard`
2. Verify forecast endpoint responds:
   - `curl -s http://localhost:8347/forecast | head`

**Pass criteria:** dashboard loads, forecast returns JSON (no 500).

---

## 2) Manual Transaction Creates Normalized Merchant
Create a manual transaction whose description includes “noise” (store number, POS, etc.).

```bash
curl -s -X POST http://localhost:8347/transactions/manual \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "Checking",
    "date": "2026-03-05",
    "description": "POS PURCHASE STARBUCKS #1234 SEATTLE WA",
    "amount": -6.54,
    "category": "Coffee",
    "source": "Manual"
  }'