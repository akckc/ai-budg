from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = get_db()

    current_balance = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions"
    ).fetchone()[0]

    # Add rest of your logic here...
    # Monthly income / expenses (SQLite version)
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

    # Spending by category (this month)
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
    # Latest 10 transactions
    transactions = conn.execute("""
        SELECT date, description, amount, category
        FROM transactions
        ORDER BY date DESC
        LIMIT 10
    """).fetchall()
    # This month income + expenses
    monthly = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) AS expenses
        FROM transactions
        WHERE date >= date_trunc('month', CURRENT_DATE)
    """).fetchone()

    income = monthly[0]
    expenses = monthly[1]
    net = income + expenses

    # Spending by category
    categories = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE amount < 0
        AND date >= date_trunc('month', CURRENT_DATE)
        GROUP BY category
        ORDER BY total ASC
    """).fetchall()

    category_labels = [row[0] for row in categories]
    category_totals = [float(row[1]) for row in categories]

    recent_transactions = conn.execute("""
    SELECT date, description, amount, category
    FROM transactions
    ORDER BY id DESC
    LIMIT 5
    """).fetchall()
    

   
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_balance": current_balance,
            "monthly_income": monthly_income,
            "income": income,
            "expenses": expenses,
            "net": net,
            "monthly_expenses": monthly_expenses,
            "monthly_net": monthly_net,
            "categories": categories,
            "transactions": transactions,
            "category_labels": category_labels,
            "recent_transactions": recent_transactions,
            "category_totals": category_totals
        }
    )
from datetime import date
from services.forecast_service import calculate_two_week_forecast

def dashboard(conn):
    current_balance = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions"
    ).fetchone()[0]

    forecast = calculate_two_week_forecast(conn, date.today())

    return render_template(
        "dashboard.html",
        current_balance=current_balance,
        projected_balance=forecast['projected_balance'],
        upcoming_items=forecast['items']
    )