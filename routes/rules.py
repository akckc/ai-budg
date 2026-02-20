from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse
from db import get_db
from pydantic import BaseModel

class RuleCreate(BaseModel):
    pattern: str
    category: str
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None

class CategoryUpdate(BaseModel):
    category: str

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
            body { font-family: Arial; padding: 30px; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background-color: #f5f5f5; }
            input { margin: 4px 0; padding: 6px; }
            button { padding: 6px 10px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h2>Category Rules</h2>

        <h3>Add Rule</h3>
        <div>
            <input id="pattern" placeholder="Pattern (e.g. AMAZON)">
            <input id="category" placeholder="Category">
            <input id="min_amount" placeholder="Min Amount (optional)">
            <input id="max_amount" placeholder="Max Amount (optional)">
            <button onclick="addRule()">Add Rule</button>
        </div>

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