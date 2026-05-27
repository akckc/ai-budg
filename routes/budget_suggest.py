from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from routes.dashboard import templates
from services.budget_suggest_service import get_budget_suggestions
from services.budget_service import set_category_budget

router = APIRouter()


class BudgetEntry(BaseModel):
    category: str
    monthly_budget: Optional[float] = None


class ApplyRequest(BaseModel):
    budgets: list[BudgetEntry]


@router.get("/budgets/suggest")
def budget_suggest_page(request: Request):
    return templates.TemplateResponse("budget_suggest.html", {"request": request})


@router.get("/budgets/suggest/data")
def budget_suggest_data():
    return get_budget_suggestions()


@router.post("/budgets/suggest/apply")
def budget_suggest_apply(body: ApplyRequest):
    applied = 0
    for entry in body.budgets:
        if entry.monthly_budget is None:
            continue
        set_category_budget(entry.category, entry.monthly_budget)
        applied += 1
    return {"success": True, "applied": applied}
