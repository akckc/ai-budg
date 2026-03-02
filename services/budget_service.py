from repositories.category_budgets_repository import (
    upsert_category_budget,
    get_all_category_budgets,
    get_spend_grouped_by_category,
)


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
