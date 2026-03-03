from fastapi import APIRouter
from services.ingestion_service import get_ingestion_history

router = APIRouter()


@router.get("/ingestion/history")
def ingestion_history(limit: int = 100):
    return get_ingestion_history(limit=limit)
