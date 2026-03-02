from fastapi import APIRouter
from db import get_db
from services.budget_service import get_spend_vs_budget_summary

router = APIRouter()


@router.get("/spend-vs-budget")
def spend_vs_budget_summary():
    # read-only summary; service is deterministic and side-effect free
    return get_spend_vs_budget_summary()
