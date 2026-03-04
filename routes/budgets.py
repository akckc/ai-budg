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
            body { font-family: Arial; padding: 30px; }
            h2, h3 { margin-bottom: 10px; }
            .form-row { margin-bottom: 16px; }
            input { margin: 4px 8px 4px 0; padding: 8px; min-width: 220px; }
            button { padding: 8px 12px; cursor: pointer; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }
            th { background-color: #f5f5f5; }
            .status { margin-top: 8px; color: #333; }
        </style>
    </head>
    <body>
        <h2>Category Budgets</h2>

        <h3>Add Budget</h3>
        <div class="form-row">
            <input id="category_name" type="text" placeholder="Category name">
            <input id="monthly_budget" type="number" step="0.01" placeholder="Monthly budget">
            <button onclick="addBudget()">Add Budget</button>
            <div id="status" class="status"></div>
        </div>

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
                            <td>${formatMoney(item.monthly_budget)}</td>
                            <td>${formatMoney(item.current_spend)}</td>
                            <td>${formatMoney(item.remaining)}</td>
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
                    return;
                }

                if (Number.isNaN(monthly_budget)) {
                    status.textContent = 'Monthly budget must be a valid number.';
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
                    return;
                }

                categoryInput.value = '';
                budgetInput.value = '';
                status.textContent = 'Budget saved.';

                loadBudgets();
            }

            loadBudgets();
        </script>
    </body>
    </html>
    """
