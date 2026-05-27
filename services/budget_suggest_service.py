from db import get_db
from repositories.budget_suggest_repository import get_90day_spend_by_category


def get_budget_suggestions() -> list[dict]:
    from routes.transactions import ALLOWED_CATEGORIES

    conn = get_db()
    try:
        spend_rows = get_90day_spend_by_category(conn)
    finally:
        conn.close()

    spend_map = {r["category"]: r["total_spend"] for r in spend_rows}

    result = []
    for category in ALLOWED_CATEGORIES:
        total = spend_map.get(category, 0.0)
        avg_monthly = round(total / 3, 2)
        result.append({
            "category": category,
            "avg_monthly": avg_monthly,
            "suggested_budget": avg_monthly,
        })

    return sorted(result, key=lambda x: x["category"])
