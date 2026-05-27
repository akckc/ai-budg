from db import get_db
from repositories.budget_suggest_repository import (
    get_90day_spend_by_category,
    get_active_recurring_monthly_by_category,
)


def get_budget_suggestions() -> list[dict]:
    from routes.transactions import ALLOWED_CATEGORIES

    conn = get_db()
    try:
        spend_rows = get_90day_spend_by_category(conn)
        recurring_rows = get_active_recurring_monthly_by_category(conn)
    finally:
        conn.close()

    spend_map = {r["category"]: r["total_spend"] for r in spend_rows}
    recurring_map = {r["category"]: r["monthly_equivalent"] for r in recurring_rows}

    result = []
    for category in ALLOWED_CATEGORIES:
        avg_monthly = round(spend_map.get(category, 0.0) / 3, 2)
        if category in recurring_map:
            suggested_budget = recurring_map[category]
        else:
            suggested_budget = avg_monthly
        result.append({
            "category": category,
            "avg_monthly": avg_monthly,
            "suggested_budget": suggested_budget,
        })

    return sorted(result, key=lambda x: x["category"])
