from db import get_db
from repositories.hygiene_repository import list_orphan_groups, bulk_reclassify


def get_orphan_groups() -> list[dict]:
    """Groups of transactions whose category is absent from category_budgets."""
    conn = get_db()
    try:
        return list_orphan_groups(conn)
    finally:
        conn.close()


def get_known_categories() -> list[str]:
    """Sorted canonical category list."""
    from routes.transactions import ALLOWED_CATEGORIES
    return sorted(ALLOWED_CATEGORIES)


def reclassify_orphan_group(current_category: str, new_category: str) -> int:
    """Bulk-reassigns transactions from current_category to new_category."""
    conn = get_db()
    try:
        return bulk_reclassify(conn, current_category, new_category)
    finally:
        conn.close()
