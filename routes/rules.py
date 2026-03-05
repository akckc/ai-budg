from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from db import get_db
from pydantic import BaseModel
from typing import Optional, List

class RuleCreate(BaseModel):
    pattern: str
    category: str
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None

class CategoryUpdate(BaseModel):
    category: str
router = APIRouter()

@router.post("/rules/add")
def add_category_rule(rule: RuleCreate):
    conn = get_db()
    conn.execute("""
        INSERT INTO category_rules (pattern, min_amount, max_amount, category)
        VALUES (?, ?, ?, ?)
    """, [rule.pattern.strip(), rule.min_amount, rule.max_amount, rule.category.strip()])
    conn.close()
    return {
        "status": "rule added",
        "rule": rule.dict()
    }

@router.get("/rules/list")
def list_rules():
    conn = get_db()

    rows = conn.execute("""
        SELECT id, pattern, min_amount, max_amount, category
        FROM category_rules
        ORDER BY pattern
    """).fetchall()

    conn.close()

    rules = [
        {
            "id": r[0],
            "pattern": r[1],
            "min_amount": r[2],
            "max_amount": r[3],
            "category": r[4]
        }
        for r in rows
    ]

    return {
        "count": len(rules),
        "rules": rules
    }

@router.get("/rules", response_class=HTMLResponse)
def rules_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Category Rules</title>
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
                padding: 12px 8px;
                text-align: left;
                border-bottom: 1px solid var(--border-default);
                font-size: 14px;
            }

            td {
                border-bottom: 1px solid var(--border-default);
                padding: 10px 8px;
                color: var(--text-primary);
                font-size: 14px;
            }

            tbody tr:hover {
                background: var(--bg-card-hover);
            }

            input {
                margin: 4px 8px 4px 0;
                padding: 8px;
                background: var(--bg-card);
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
        <h2>Category Rules</h2>
        <a href="/dashboard">← Back to Dashboard</a>

        <div class="card">
            <h3>Add Rule</h3>
            <div>
                <input id="pattern" placeholder="Pattern (e.g. AMAZON)">
                <input id="category" placeholder="Category">
                <input id="min_amount" placeholder="Min Amount (optional)">
                <input id="max_amount" placeholder="Max Amount (optional)">
                <button onclick="addRule()">Add Rule</button>
            </div>
        </div>

        <div class="card">
            <h3>Existing Rules</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Pattern</th>
                        <th>Min</th>
                        <th>Max</th>
                        <th>Category</th>
                    </tr>
                </thead>
                <tbody id="rulesTable"></tbody>
            </table>
        </div>

        <script>
            async function loadRules() {
                const res = await fetch('/rules/list');
                const data = await res.json();

                const table = document.getElementById('rulesTable');
                table.innerHTML = '';

                data.rules.forEach(rule => {
                    const row = `
                        <tr>
                            <td>${rule.id}</td>
                            <td>${rule.pattern}</td>
                            <td>${rule.min_amount ?? ''}</td>
                            <td>${rule.max_amount ?? ''}</td>
                            <td>${rule.category}</td>
                        </tr>
                    `;
                    table.innerHTML += row;
                });
            }

            async function addRule() {
                const pattern = document.getElementById('pattern').value;
                const category = document.getElementById('category').value;
                const min_amount = document.getElementById('min_amount').value;
                const max_amount = document.getElementById('max_amount').value;

                await fetch('/rules/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        pattern,
                        category,
                        min_amount: min_amount || null,
                        max_amount: max_amount || null
                    })
                });

                document.getElementById('pattern').value = '';
                document.getElementById('category').value = '';
                document.getElementById('min_amount').value = '';
                document.getElementById('max_amount').value = '';

                loadRules();
            }

            loadRules();
        </script>
    </body>
    </html>
    """