from db import get_db
from repositories.hygiene_repository import list_orphan_groups, bulk_reclassify
from repositories.category_budgets_repository import get_all_category_budgets


def get_orphan_groups() -> list[dict]:
    """Groups of transactions whose category is absent from category_budgets."""
    conn = get_db()
    try:
        return list_orphan_groups(conn)
    finally:
        conn.close()


def get_known_categories() -> list[str]:
    """Sorted list of valid categories drawn from category_budgets."""
    return sorted(b["category_name"] for b in get_all_category_budgets())


def reclassify_orphan_group(current_category: str, new_category: str) -> int:
    """Bulk-reassigns transactions from current_category to new_category."""
    conn = get_db()
    try:
        return bulk_reclassify(conn, current_category, new_category)
    finally:
        conn.close()
