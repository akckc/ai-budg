📜 Budget-AI Design Authority (DA) v1.1
1. Mission

Budget-AI helps two humans know, at any given moment, how much money they can safely spend — without punishing missed entries — while providing forgiving and transparent forecasting.

The system:

Reduces friction

Tolerates imperfection

Prioritizes actionable insight over perfect accounting

2. Core Capabilities
Tier 0 – Non-Negotiable (Do Not Break)

These capabilities are mandatory. No feature may degrade or bypass them.

Manual Transaction Entry
Users can add transactions quickly; updates ledger and forecast immediately.

Transaction Edit/Delete
Users can modify or remove any transaction.

CSV Import
Users can reconcile bank data.

Deduplication enforced

Unmatched transactions auto-imported

Recurring Transactions
Forecast engine applies recurring income and bills correctly.

Safe-to-Spend Calculation
Updated in real time using cash-flow-based logic.

Forecast Engine

Deterministic two-week projection

Includes recurring + imported transactions

Service Layer Compliance
All writes go through the service layer.
❌ No direct DB writes.

Reconciliation Safety
Reconciled transactions augment history.
❌ Never delete or overwrite manual entries.

Tier 1 – Core Experience

Category assignment (manual + rule-based)

Budget per category

Visual spend vs budget (charts/graphs)

Multi-account tracking

Tier 2 – Growth / Future Intelligence

AI trend analysis

Suggested budget corrections

Spending warnings

Predictive modeling

Merchant normalization / alias mapping

Constraint: Tier 2 features must never break Tier 0 capabilities.

3. Financial Engine Definition
Safe-to-Spend Formula
Safe-to-Spend =
Current Available Balance
− Known Upcoming Transactions
+ Known Upcoming Income
(forecasted through next paycheck)
Forecast Assumptions

Deterministic two-week projection window

Recurring items stored as templates (never inferred silently)

Safe-to-Spend is cash-flow authoritative

Budgets are advisory only

4. System Invariants

These invariants must hold true at all times.

Ledger Authority
Ledger is the single source of truth.

Service Layer Enforcement
All transaction writes go through the service layer.

Determinism
Forecast outputs must be reproducible for the same dataset.

Reconciliation Safety
Reconciled transactions augment, never delete or silently mutate entries.

Budget Advisory Constraint
Budgeting layer cannot override cash-flow calculations.

Multi-Account Consistency
All calculations must account for every active account.

5. Architecture Principles

Thin routes (no business logic in routes)

Business logic lives exclusively in the service layer

Repository layer handles DB access only

Idempotent ingestion required

Multi-account support is first-class

Deterministic rule evaluation for category automation

Schema constraints enforced consistently

6. Thread Roles & Responsibilities
PM Thread

Sprint planning and prioritization

References DA

Does not merge code

Execution / Sprint Threads

Draft features and propose changes

Must explicitly reference DA v1.1

Cannot merge directly

Authoritative Thread

Reviews proposals

Validates against Tier 0 + invariants

Merges approved changes

Maintains canonical code

Meta Thread

Workflow discussion only

No code edits

7. Proposal & Merge Protocol

Sprint generates proposed code changes.

Submit proposal to Authoritative thread.

Review against:

Tier 0 checklist

System invariants

Validated proposals merged into canonical codebase.

Merged changes documented in changelog.

8. Reference Protocol

All sprint proposals must explicitly cite DA v1.1.

No feature may violate Tier 0 without formal DA revision.

9. Versioning Rules

DA updates require deliberate versioning (v1.2, v2.0, etc.).

Sprint threads may propose DA changes but cannot edit directly.

Authoritative thread or PM approves revisions.

10. Sprint Completion Checklist

Before marking a sprint complete:

☐ Add transaction (manual)

☐ Edit transaction

☐ Delete transaction

☐ Import CSV

☐ Reconcile imported transactions

☐ Verify Safe-to-Spend calculation

☐ Forecast includes recurring items correctly

☐ Multi-account consistency verified

☐ Service layer compliance verified

Governance Note

The Design Authority governs all architectural and financial logic decisions within Budget-AI.
When in doubt: Tier 0 protection overrides feature velocity.