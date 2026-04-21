# Budget-AI — Claude Code Context

## Project Summary
Household cash-flow forecasting app. The goal is to tell two people how much they can
safely spend at any moment. It is **not** a traditional budgeting tool.

- **Stack**: Python / FastAPI, DuckDB, Jinja2, Docker (Unraid), Cloudflare Tunnel
- **Dev workflow**: Develop on Windows → push to GitHub → pull to Unraid → test in container
- **Container**: `budget-api-dev`
- **DB path**: `data/budget.duckdb`
- **Python**: `/usr/local/bin/python`

---

## Architecture Rules (Non-Negotiable)

These invariants must hold after every change:

1. **Thin routes** — no business logic in `routes/`. Routes only parse HTTP input and call services.
2. **Service layer owns logic** — all business logic lives in `services/`.
3. **Repository layer owns DB access** — `repositories/` does reads/writes only; no logic.
4. **No direct DB writes in routes** — ever.
5. **Forecast engine is read-only and deterministic** — given identical ledger state, recurring
   templates, and `as_of_date`, output must be reproducible. No side effects.
6. **Budgets are advisory only** — the budget layer must never override cash-flow calculations.
7. **Multi-account is first-class** — all balance/forecast calculations must span all active accounts.
8. **Reconciliation augments, never destroys** — reconciled transactions update manual entries;
   they never silently delete or overwrite them.

---

## Tier 0 — Do Not Break

Before marking any task complete, verify these still work:

- [ ] Manual transaction add
- [ ] Transaction edit / delete
- [ ] CSV import (deduplication enforced, unmatched rows auto-imported)
- [ ] Reconciliation workflow
- [ ] Safe-to-Spend calculation
- [ ] Forecast includes recurring items correctly

---

## Key Files

| File | Purpose |
|---|---|
| `services/projection_service.py` | Authoritative 14-day projection engine |
| `services/forecast_service.py` | Legacy wrapper; reshapes projection output for templates |
| `services/recurring_service.py` | Recurring event CRUD |
| `repositories/transaction_reconciliation_repository.py` | Fuzzy matching + reconciliation writes |
| `models/projection_dto.py` | `DailyProjection`, `ProjectionResult` DTOs |
| `routes/forecast.py` | `/forecast` endpoint → `ForecastDayDTO` |
| `templates/dashboard.html` | Main UI (Chart.js burndown chart lives here) |
| `docs/design_authority.md` | Design Authority — source of truth for constraints |
| `docs/PROJECT_PLAN.md` | Sprint history and forward plan |

---

## Critical Patterns

### `allow_consume` flag
Distinguishes how recurring events interact with matching transactions:
- **`allow_consume = True`** (e.g. fixed bills): a matching transaction *consumes* the
  forecast occurrence — it will not be double-counted in the projection.
- **`allow_consume = False`** (e.g. variable spending): the recurring item always appears
  in the forecast regardless of matching transactions.

### `_is_consumed()` helper
Uses a date-tolerance window (not exact-date matching) when checking whether a transaction
has already satisfied a recurring event occurrence. Do not tighten this to exact-date matching.

### Forecast pipeline
`DailyProjection` → `ProjectionResult` → `/forecast` route → `ForecastDayDTO` → Chart.js

Tooltip data (scheduled recurring events per day) flows through `ForecastDayDTO`.
Do not add financial logic to the DTO layer.

### Reconciliation scoring
Fuzzy match confidence thresholds:
- **≥ 90%** → auto-matched
- **70–89%** → review queue
- **< 70%** → unmatched (insert as new)

Scoring weights: Amount (40pts, ≤2% variance), Date (30pts, ±1 day), Description (30pts).

---

## Preferred Approach

- **Additive solutions first** — prefer changes that require no schema migrations, no new
  endpoints, and no modifications to financial logic.
- **Pragmatic over perfect** — defer manageable imperfections rather than over-engineer.
- **Validate backlog items against actual code** — do not assume schema or service methods
  exist just because they appear in design notes or prior sprint plans.

---

## Design Authority Reference

Before proposing schema changes, forecast engine modifications, or Safe-to-Spend logic
changes, re-read `docs/design_authority.md`. Changes to those areas require explicit DA review.

Sprint proposals use `.github/pull_request_template.md`.

---

## Known Gotchas

- **Starlette `TemplateResponse` signature**: The new API is `TemplateResponse(request, name, context)`
  — `request` is the first positional arg, not inside the context dict. The old `(name, context)` form
  was removed in a Starlette upgrade. Affects `routes/dashboard.py`, `routes/transactions.py`,
  `routes/reconciliation.py` (already fixed). Any new template route must use the new signature.

---

## Open Backlog (as of last update)

- Investigate auto-tagging miss on mortgage transaction during CSV import
- `PROJECT_PLAN.md` rewrite (archive sprint history to `docs/SPRINT_LOG.md`)
- `README.md` update to reflect current reconciliation workflow
- Review open GitHub issues and incorporate into project plan
