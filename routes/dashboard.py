from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import date
from db import get_db
from services.forecast_service import calculate_two_week_forecast

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

    # --- Two-week forecast ---
    try:
        forecast = calculate_two_week_forecast(conn, date.today())
        projected_balance = forecast['projected_balance']
        upcoming_items = forecast['items']
    except Exception as e:
        print("Forecast error:", e)
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
            "upcoming_items": upcoming_items
        }
    )
from fastapi import Form
from fastapi.responses import RedirectResponse
from repositories.accounts_repository import get_or_create_account
from services.transaction_service import add_transaction

# -------------------------
# MANUAL TRANSACTION FORM SUBMISSION
# -------------------------
@router.post("/transactions/manual")
def add_manual_transaction_form(
    date: str = Form(...),
    description: str = Form(...),
    amount: float = Form(...),
    category: str = Form(None),
    account_name: str = Form("Primary Account"),
):
    """
    Handles HTML form submission from dashboard add transaction card.
    """
    # Ensure account exists
    account = get_or_create_account(account_name)
    account_id = account["id"]

    try:
        add_transaction(
            account_id=account_id,
            date=date,
            description=description,
            amount=amount,
            balance=None,
            category=category,
            source="Manual",
        )
    except Exception as e:
        # Could log here if desired
        return {"success": False, "error": str(e)}

    # Redirect back to dashboard after submission
    return RedirectResponse(url="/dashboard", status_code=303)