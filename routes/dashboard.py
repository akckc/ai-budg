from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import date
from db import get_db
from services.forecast_service import calculate_two_week_forecast
from services.projection_service import calculate_two_week_projection
from services.budget_service import get_spend_vs_budget_summary

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = get_db()

    # --- Current balance ---
    current_balance = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions"
    ).fetchone()[0]

    # Spend vs budget summary (Sprint 8)
    spend_vs_budget = get_spend_vs_budget_summary()

    # --- Monthly income / expenses ---
    monthly = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) AS expenses
        FROM transactions
        WHERE date >= date_trunc('month', CURRENT_DATE)
    """).fetchone()
    monthly_income = monthly[0]
    monthly_expenses = monthly[1]
    monthly_net = monthly_income + monthly_expenses

    # --- Spending by category ---
    categories = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE amount < 0
        AND date >= date_trunc('month', CURRENT_DATE)
        GROUP BY category
        ORDER BY total ASC
    """).fetchall()
    category_labels = [row[0] for row in categories]
    category_totals = [float(abs(row[1])) for row in categories]

    # --- Recent transactions ---
    recent_transactions = conn.execute("""
        SELECT date, description, amount, category
        FROM transactions
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    # --- Two-week projection (new deterministic engine) ---
    try:
        projection = calculate_two_week_projection()
        projected_balance = projection.timeline[-1].projected_balance
        # still call legacy forecast service for item list so template
        # remains unchanged
        forecast = calculate_two_week_forecast(conn, date.today())
        upcoming_items = forecast['items']
    except Exception as e:
        print("Projection error:", e)
        projected_balance = 0.0
        upcoming_items = []
    
            

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_balance": current_balance,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "monthly_net": monthly_net,
            "categories": categories,
            "category_labels": category_labels,
            "category_totals": category_totals,
            "recent_transactions": recent_transactions,
            "projected_balance": projected_balance,
            "upcoming_items": upcoming_items,
            "spend_vs_budget": spend_vs_budget,
        }
    )
from fastapi import Form, HTTPException
from fastapi.responses import RedirectResponse
from repositories.accounts_repository import get_or_create_account
from services.transaction_service import add_transaction

# -------------------------
# MANUAL TRANSACTION FORM SUBMISSION
# -------------------------
@router.post("/transactions/manual")
async def add_manual_transaction_form(request: Request):
    """
    Handles both HTML form submissions (from dashboard) and JSON API calls.

    - application/json → returns JSON {"success": true, "message": "..."}
    - application/x-www-form-urlencoded → redirects back to /dashboard
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
        account_name = data.get("account_name", "Primary Account")
        date_val = data.get("date")
        description = data.get("description")
        raw_amount = data.get("amount")
        if raw_amount is None:
            raise HTTPException(status_code=400, detail="amount is required")
        amount = float(raw_amount)
        balance = float(data.get("balance")) if data.get("balance") not in (None, "") else None
        category = data.get("category")
        source = data.get("source", "manual")
    else:
        form = await request.form()
        account_name = form.get("account_name", "Primary Account")
        date_val = form.get("date")
        description = form.get("description")
        raw_amount = form.get("amount")
        if raw_amount is None:
            raise HTTPException(status_code=400, detail="amount is required")
        amount = float(raw_amount)
        balance = float(form.get("balance")) if form.get("balance") not in (None, "") else None
        category = form.get("category")
        source = form.get("source", "manual")

    account = get_or_create_account(account_name)
    account_id = account["id"]

    try:
        add_transaction(
            account_id=account_id,
            date=date_val,
            description=description,
            amount=amount,
            balance=balance,
            category=category,
            source=source,
        )
    except Exception as e:
        if "application/json" in content_type:
            raise HTTPException(status_code=400, detail=f"Insert failed: {e}")
        return {"success": False, "error": str(e)}

    if "application/json" in content_type:
        return {"success": True, "message": "Transaction added"}

    # Redirect back to dashboard after HTML form submission
    return RedirectResponse(url="/dashboard", status_code=303)