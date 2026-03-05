from fastapi import APIRouter
from fastapi.responses import HTMLResponse
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


@router.get("/budgets", response_class=HTMLResponse)
def budgets_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Category Budgets</title>
        <style>
            :root {
                --bg-main: #2F2F2F;
                --bg-card: #3A3A3A;
                --bg-card-hover: #444444;
                --border-default: #505050;
                --text-primary: #F2F2F2;
                --text-secondary: #C8C8C8;
                --text-muted: #9A9A9A;
                --color-income: #3FB950;
                --color-expense: #F85149;
                --color-budget: #58A6FF;
                --color-warning: #F2CC60;
            }

            body {
                font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                padding: 32px;
                background: var(--bg-main);
                color: var(--text-primary);
                margin: 0;
            }

            h2 {
                font-size: 28px;
                margin: 0 0 32px 0;
                color: var(--text-primary);
            }

            h3 {
                font-size: 16px;
                margin: 24px 0 16px 0;
                color: var(--text-primary);
                font-weight: 600;
            }

            .card {
                background: var(--bg-card);
                border: 1px solid var(--border-default);
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 24px;
            }

            .form-row {
                margin-bottom: 16px;
            }

            input {
                margin: 4px 8px 4px 0;
                padding: 8px;
                min-width: 220px;
                background: var(--bg-main);
                border: 1px solid var(--border-default);
                color: var(--text-primary);
                border-radius: 6px;
                font-size: 14px;
            }

            input::placeholder {
                color: var(--text-muted);
            }

            input:focus {
                outline: none;
                border-color: var(--color-budget);
                box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.1);
            }

            button {
                padding: 8px 14px;
                cursor: pointer;
                background: var(--color-budget);
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                transition: background 0.2s;
            }

            button:hover {
                background: #6CB6FF;
            }

            table {
                border-collapse: collapse;
                width: 100%;
                background: var(--bg-card);
                margin-top: 16px;
            }

            th {
                background-color: var(--bg-card);
                color: var(--text-secondary);
                font-weight: 600;
                padding: 12px 10px;
                text-align: left;
                border-bottom: 1px solid var(--border-default);
                font-size: 14px;
            }

            td {
                border-bottom: 1px solid var(--border-default);
                padding: 10px;
                color: var(--text-primary);
                font-size: 14px;
            }

            tbody tr:hover {
                background: var(--bg-card-hover);
            }

            .status {
                margin-top: 8px;
                color: var(--text-secondary);
                font-size: 14px;
                min-height: 20px;
            }

            .status.success {
                color: var(--color-income);
            }

            .status.error {
                color: var(--color-expense);
            }

            a {
                color: var(--color-budget);
                text-decoration: none;
            }

            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <h2>Category Budgets</h2>
        <a href="/dashboard">← Back to Dashboard</a>

        <div class="card">
            <h3>Add Budget</h3>
            <div class="form-row">
                <input id="category_name" type="text" placeholder="Category name">
                <input id="monthly_budget" type="number" step="0.01" placeholder="Monthly budget">
                <button onclick="addBudget()">Add Budget</button>
                <div id="status" class="status"></div>
            </div>
        </div>

        <div class="card">
            <h3>Existing Budgets</h3>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Monthly Budget</th>
                        <th>Current Spend</th>
                        <th>Remaining</th>
                        <th>Active</th>
                    </tr>
                </thead>
                <tbody id="budgetsTable"></tbody>
            </table>
        </div>

        <script>
            function formatMoney(value) {
                if (value === null || value === undefined || value === '') {
                    return '';
                }
                const number = Number(value);
                if (Number.isNaN(number)) {
                    return value;
                }
                return number.toFixed(2);
            }

            async function loadBudgets() {
                const res = await fetch('/budgets/summary');
                const data = await res.json();

                const table = document.getElementById('budgetsTable');
                table.innerHTML = '';

                data.forEach(item => {
                    const row = `
                        <tr>
                            <td>${item.category_name ?? ''}</td>
                            <td style="color: var(--color-budget); font-weight: 600;">$${formatMoney(item.monthly_budget)}</td>
                            <td style="color: var(--color-expense);">${formatMoney(item.current_spend)}</td>
                            <td style="color: var(--color-income); font-weight: 600;">$${formatMoney(item.remaining)}</td>
                            <td>${item.active ? 'Yes' : 'No'}</td>
                        </tr>
                    `;
                    table.innerHTML += row;
                });
            }

            async function addBudget() {
                const categoryInput = document.getElementById('category_name');
                const budgetInput = document.getElementById('monthly_budget');
                const status = document.getElementById('status');

                const category_name = categoryInput.value.trim();
                const monthly_budget = Number(budgetInput.value);

                if (!category_name) {
                    status.textContent = 'Category name is required.';
                    status.classList.add('error');
                    return;
                }

                if (Number.isNaN(monthly_budget)) {
                    status.textContent = 'Monthly budget must be a valid number.';
                    status.classList.add('error');
                    return;
                }

                const res = await fetch('/budgets/category', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        category_name,
                        monthly_budget
                    })
                });

                if (!res.ok) {
                    status.textContent = 'Failed to add budget.';
                    status.classList.add('error');
                    return;
                }

                categoryInput.value = '';
                budgetInput.value = '';
                status.textContent = 'Budget saved.';
                status.classList.remove('error');
                status.classList.add('success');

                loadBudgets();
            }

            loadBudgets();
        </script>
    </body>
    </html>
    """
