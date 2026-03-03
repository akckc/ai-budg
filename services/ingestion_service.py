from repositories.ingestion_repository import get_ingestion_history as repo_get_ingestion_history


def get_ingestion_history(limit: int = 100) -> list[dict]:
    return repo_get_ingestion_history(limit=limit)
