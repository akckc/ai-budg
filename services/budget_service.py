from repositories.category_budgets_repository import (
    upsert_category_budget,
    get_all_category_budgets,
    get_spend_grouped_by_category,
)

# repository import already includes spend aggregation; we'll use it for the new summary


def set_category_budget(category_name: str, monthly_budget: float, active: bool = True) -> None:
    """
    Creates or updates a category budget configuration.
    Deterministic. No ledger mutation.
    """
    upsert_category_budget(category_name, monthly_budget, active)


def get_category_budget_summary() -> list[dict]:
    """
    Returns list of summary dicts containing:
      - category_name
      - monthly_budget
      - current_spend
      - remaining
      - active

    Deterministic read-only aggregation. No side effects.
    """
    budgets = get_all_category_budgets()
    spend = get_spend_grouped_by_category()

    spend_lookup = {s["category_name"]: s["current_spend"] for s in spend}

    summary = []

    for b in budgets:
        category_name = b["category_name"]
        monthly_budget = b["monthly_budget"]
        active = b["active"]
        current_spend = spend_lookup.get(category_name, 0.0)

        remaining = None
        if monthly_budget is not None:
            remaining = monthly_budget - current_spend

        summary.append(
            {
                "category_name": category_name,
                "monthly_budget": monthly_budget,
                "current_spend": current_spend,
                "remaining": remaining,
                "active": active,
            }
        )

    return summary


# ------------------------------------------------------------------
# New function for Sprint 8
# ------------------------------------------------------------------

def get_spend_vs_budget_summary() -> list[dict]:
    """
    Deterministic aggregation of total spend per category compared against
    configured budget.

    Returns a list of dictionaries containing:
        category, budget, spent, remaining

    Read-only. No side effects.
    """
    # reuse existing repository helpers; they open/close their own connections
    budgets = get_all_category_budgets()
    spend_entries = get_spend_grouped_by_category()

    # build lookup maps (filter out None categories)
    budget_map = {b["category_name"]: float(b["monthly_budget"] or 0.0) for b in budgets if b["category_name"] is not None}
    spend_map = {s["category_name"]: float(s["current_spend"]) for s in spend_entries if s["category_name"] is not None}

    # deterministic ordering by category name
    categories = sorted(set(budget_map.keys()) | set(spend_map.keys()))

    result = []
    for cat in categories:
        spent = round(spend_map.get(cat, 0.0), 2)
        budget = round(budget_map.get(cat, 0.0), 2)
        remaining = round(budget - spent, 2)
        result.append({
            "category": cat,
            "budget": budget,
            "spent": spent,
            "remaining": remaining,
        })
    return result
