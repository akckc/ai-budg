from fastapi import APIRouter
from pydantic import BaseModel
from services.budget_service import (
    set_category_budget,
    get_category_budget_summary,
)

router = APIRouter()


class CategoryBudgetRequest(BaseModel):
    category_name: str
    monthly_budget: float
    active: bool = True


@router.post("/budgets/category")
def create_or_update_category_budget(request: CategoryBudgetRequest):
    set_category_budget(
        category_name=request.category_name,
        monthly_budget=request.monthly_budget,
        active=request.active,
    )
    return {"status": "ok"}


@router.get("/budgets/summary")
def category_budget_summary():
    return get_category_budget_summary()
