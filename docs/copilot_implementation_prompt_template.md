You are implementing an approved Budget-AI sprint feature.

Follow Design Authority v1.1 strictly.

========================================
FEATURE
========================================

Feature Name:
<Feature Name>

Short Description:
<1–3 sentence summary>

========================================
ARCHITECTURAL DESIGN SUMMARY
========================================

<System-level explanation from Sprint Proposal>

Data Flow:
<Route → Service → Repository → DB → Service → Route>

Layer Responsibilities:

Routes:
- No business logic
- Call service layer only

Services:
- All business logic
- Deterministic calculations only
- No direct DB access

Repositories:
- CRUD operations only
- No business logic

========================================
FILES IN SCOPE
========================================

Modify ONLY these files:

- path/to/file.py
- path/to/file.py

New files allowed:
- path/to/new_file.py

Do NOT modify any other files.

========================================
FUNCTION CONTRACTS
========================================

Define or implement the following functions exactly:

def example_function(arg1: type, arg2: type) -> ReturnType:
    """
    Deterministic behavior.
    No side effects.
    """

========================================
DA v1.1 CONSTRAINTS (MANDATORY)
========================================

- No DB access outside repository layer
- No business logic in routes
- No repository logic inside services
- Deterministic forecast behavior must be preserved
- No side effects in read operations
- Reconciliation safety must remain intact
- Do not alter balance calculation logic unless explicitly specified

========================================
OUTPUT FORMAT
========================================

1. Show full code for new files.
2. Show exact diffs for modified files.
3. Do not refactor unrelated code.
4. Do not add enhancements beyond scope.
5. Keep implementation minimal and clean.

Begin implementation.