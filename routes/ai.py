from fastapi import APIRouter
from services.ai_categorization_service import run_ai_reclassify_uncategorized

router = APIRouter()


@router.post("/ai/reclassify_uncategorized")
def reclassify_uncategorized(max_merchants: int = None):
    """
    Call AI categorization service and return JSON summary.
    No business logic in route; service handles orchestration.
    """
    result = run_ai_reclassify_uncategorized(max_merchants=max_merchants)
    return result
