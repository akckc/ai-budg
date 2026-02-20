from fastapi import FastAPI, UploadFile, File
import duckdb
from pathlib import Path
import requests
import csv
import io
import os
from datetime import datetime
from typing import List, Dict, Any
import json
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import RedirectResponse
from fastapi import Form 
from fastapi.responses import RedirectResponse

class RuleCreate(BaseModel):
    pattern: str
    category: str
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None

class CategoryUpdate(BaseModel):
    category: str



app = FastAPI()
@app.on_event("startup")
def startup():
    init_db()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
# Database setup
DB_PATH = "/app/data/budget.db"

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS transactions_id_seq
        START 1
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY DEFAULT nextval('transactions_id_seq'),

            date DATE NOT NULL,
            description VARCHAR NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            balance DECIMAL(10,2),
            category VARCHAR,

            source VARCHAR NOT NULL DEFAULT 'unknown',

            account_id INTEGER NULL,
            user_id INTEGER NULL,
            merchant_id INTEGER NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS category_rules_id_seq START 1;
    """)
    conn.execute("""    
        CREATE TABLE IF NOT EXISTS category_rules (
            id INTEGER PRIMARY KEY DEFAULT nextval('category_rules_id_seq'),
            pattern VARCHAR NOT NULL,
            min_amount DECIMAL(10,2),
            max_amount DECIMAL(10,2),
            category VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.close()

def get_db():
    conn = duckdb.connect(DB_PATH)
    return conn





# LEGACY: transitional in-memory buffer. 
#latest_transactions = []

@app.get("/health/ollama")
def ollama_health():
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": "qwen2.5:14b",
            "prompt": "Reply with the single word: OK",
            "stream": False
        },
        timeout=60
    )
    return r.json()

@app.post("/transactions/manual")
def add_manual_transaction(txn: dict):
    required = ["date", "description", "amount", "category","source"]
    for field in required:
        if field not in txn:
            return {"error": f"Missing required field: {field}"}

    conn = get_db()

    conn.execute("""
        INSERT INTO transactions (
            date,
            description,
            amount,
            category,
            source,
            account_id,
            user_id
        ) VALUES (?, ?, ?, ?, 'manual', ?, ?)
    """, [
        txn["date"],
        txn["description"].strip(),
        txn["amount"],
        txn["category"].strip(),
        txn.get("account_id"),
        txn.get("user_id")
    ])

    conn.close()

    return {"success": True}

@app.post("/rules/add")
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

@app.get("/rules/list")
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

@app.post("/upload/csv")
def upload_csv(file: UploadFile = File(...)):
    contents = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(contents))

    conn = get_db()

    inserted = 0
    skipped = 0

    for row in reader:
        txn = normalize_row(row)  # ← your existing normalization logic

        # Optional dedupe check (recommended)
        exists = conn.execute("""
            SELECT 1 FROM transactions
            WHERE date = ?
              AND description = ?
              AND amount = ?
              AND balance = ?
        """, [
            txn["date"],
            txn["description"],
            txn["amount"],
            txn.get("balance")
        ]).fetchone()

        if exists:
            skipped += 1
            continue

        conn.execute("""
    INSERT INTO transactions (
        id,
        date,
        description,
        amount,
        balance,
        category,
        source
    ) VALUES (nextval('transactions_id_seq'), ?, ?, ?, ?, NULL,'csv')
""", [
            txn["date"],
            txn["description"],
            txn["amount"],
            txn.get("balance")
        ])

        inserted += 1

    conn.close()

    return {
        "success": True,
        "inserted": inserted,
        "skipped": skipped
    }


@app.post("/normalize/csv")
async def normalize_csv(file: UploadFile = File(...)):
    contents = await file.read()
    reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))

    conn = get_db()

    inserted = 0
    skipped = 0

    for row in reader:
        # Normalize fields (same as before)
        date_str = row.get("Date", "").strip()
        if date_str:
            date_obj = datetime.strptime(date_str, "%m/%d/%Y")
            iso_date = date_obj.strftime("%Y-%m-%d")
        else:
            iso_date = None

        amount_str = row.get("Amount", "").strip()
        if amount_str:
            amount_str = amount_str.replace("$", "").replace(",", "")
            if amount_str.startswith("(") and amount_str.endswith(")"):
                amount = -float(amount_str.strip("()"))
            elif amount_str.startswith("-"):
                amount = float(amount_str)
            else:
                amount = float(amount_str)
        else:
            amount = None

        balance_str = row.get("Balance", "").strip()
        if balance_str:
            balance_str = balance_str.replace("$", "").replace(",", "")
            balance = float(balance_str)
        else:
            balance = None

        # Dedup against DB
        exists = conn.execute("""
            SELECT 1 FROM transactions
            WHERE date = ?
              AND description = ?
              AND amount = ?
              AND balance = ?
        """, [iso_date, row.get("Description","").strip(), amount, balance]).fetchone()

        if exists:
            skipped += 1
            continue

        # Insert with category NULL
        conn.execute("""
    INSERT INTO transactions (
        id,
        date,
        description,
        amount,
        balance,
        category,
        source
    ) VALUES (nextval('transactions_id_seq'), ?, ?, ?, ?, NULL,'csv')
""", [iso_date, row.get("Description","").strip(), amount, balance])

        inserted += 1

    # Close DB
    conn.close()

    return {
        "success": True,
        "filename": file.filename,
        "inserted": inserted,
        "skipped": skipped
    }


@app.post("/categorize/pending")
def categorize_pending(limit: int = 20):
    """
    Categorize uncategorized transactions.
    1) Apply deterministic category_rules
    2) Send remaining rows to Ollama
    """

    conn = get_db()

    # Fetch rules
    rules = conn.execute("""
        SELECT pattern, min_amount, max_amount, category
        FROM category_rules
        ORDER BY length(pattern) DESC, min_amount DESC
    """).fetchall()

    # Fetch uncategorized transactions
    rows = conn.execute("""
        SELECT id, date, description, amount
        FROM transactions
        WHERE category IS NULL
        ORDER BY date
        LIMIT ?
    """, [limit]).fetchall()

    if not rows:
        conn.close()
        return {"status": "nothing to categorize"}

    resolved_ids = set()
    remaining_rows = []

    # ----------------------------
    # 1) APPLY RULES FIRST
    # ----------------------------
    for txn_id, date, desc, amount in rows:
        matched = False

        for pattern, min_amt, max_amt, category in rules:
            if desc and pattern.lower() in desc.lower():
                if (min_amt is None or amount >= min_amt) and \
                   (max_amt is None or amount <= max_amt):

                    conn.execute("""
                        UPDATE transactions
                        SET category = ?
                        WHERE id = ?
                    """, [category, txn_id])

                    resolved_ids.add(txn_id)
                    matched = True
                    break

        if not matched:
            remaining_rows.append((txn_id, date, desc, amount))

    # If rules handled everything, skip LLM
    if not remaining_rows:
        conn.close()
        return {
            "requested": len(rows),
            "updated": len(resolved_ids),
            "via_rules": len(resolved_ids),
            "via_llm": 0
        }

    # ----------------------------
    # 2) BUILD LLM PROMPT
    # ----------------------------
    lines = [
        f"ID {r[0]} | {r[1]} | {r[2]} | ${r[3]:.2f}"
        for r in remaining_rows
    ]

    prompt = f"""
You are categorizing financial transactions.

Return ONLY valid JSON in this exact format:
[
  {{ "id": 123, "category": "Groceries" }}
]

Use short, common category names.
Do not include explanations.

Transactions:
{chr(10).join(lines)}
"""

    # ----------------------------
    # 3) CALL OLLAMA
    # ----------------------------
    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": "qwen2.5:14b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 500
            }
        },
        timeout=300
    )

    if resp.status_code != 200:
        conn.close()
        return {"error": "Ollama request failed", "details": resp.text}

    try:
        data = json.loads(resp.json()["response"])
    except Exception:
        conn.close()
        return {
            "error": "Failed to parse LLM response",
            "raw_response": resp.json().get("response")
        }

    # ----------------------------
    # 4) UPDATE FROM LLM
    # ----------------------------
    llm_updated = 0

    for item in data:
        if "id" not in item or "category" not in item:
            continue

        conn.execute("""
            UPDATE transactions
            SET category = ?
            WHERE id = ?
        """, [item["category"], item["id"]])

        llm_updated += 1

    conn.close()

    return {
        "requested": len(rows),
        "updated": len(resolved_ids) + llm_updated,
        "via_rules": len(resolved_ids),
        "via_llm": llm_updated
    }



@app.get("/transactions/from-db")
def get_transactions_from_db():
    """Retrieve all transactions from DuckDB"""
    conn = get_db()
    
    result = conn.execute("""
        SELECT id, date, description, amount, balance, category, created_at
        FROM transactions
        ORDER BY date DESC
    """).fetchall()
    
    columns = ['id', 'date', 'description', 'amount', 'balance', 'category', 'created_at']
    transactions = [dict(zip(columns, row)) for row in result]
    
    conn.close()
    
    return {
        "transaction_count": len(transactions),
        "transactions": transactions
    }

@app.get("/transactions/stats")
def get_transaction_stats():
    """Get spending statistics by category"""
    conn = get_db()
    
    # Total by category
    category_totals = conn.execute("""
        SELECT 
            category,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount
        FROM transactions
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY total_amount ASC
    """).fetchall()
    
    # Overall stats
    overall = conn.execute("""
        SELECT 
            COUNT(*) as total_transactions,
            SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_spent,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
            MIN(date) as earliest_date,
            MAX(date) as latest_date
        FROM transactions
    """).fetchone()
    
    conn.close()
    
    return {
        "by_category": [
            {
                "category": row[0],
                "count": row[1],
                "total": float(row[2]),
                "average": float(row[3])
            }
            for row in category_totals
        ],
        "overall": {
            "total_transactions": overall[0],
            "total_spent": float(overall[1]) if overall[1] else 0,
            "total_income": float(overall[2]) if overall[2] else 0,
            "date_range": f"{overall[3]} to {overall[4]}" if overall[3] else None
        }
    }
@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")

@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Budget Categorizer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        
        .upload-section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 6px;
        }
        
        .button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 10px;
        }
        
        .button:hover {
            background: #0056b3;
        }
        
        .button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .button-success {
            background: #28a745;
        }
        
        .button-success:hover {
            background: #218838;
        }
        
        input[type="file"] {
            margin-right: 10px;
        }
        
        .status {
            margin-top: 15px;
            padding: 10px;
            border-radius: 4px;
            display: none;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
            position: sticky;
            top: 0;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .category-cell {
            display: flex;
            gap: 5px;
            align-items: center;
        }
        
        .category-input {
            padding: 5px 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            width: 180px;
        }
        
        .amount-positive {
            color: #28a745;
            font-weight: 500;
        }
        
        .amount-negative {
            color: #dc3545;
            font-weight: 500;
        }
        
        .stats {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        
        .stat-item {
            flex: 1;
        }
        
        .stat-label {
            font-size: 12px;
            color: #6c757d;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: 600;
            color: #333;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #007bff;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .filter-section {
            margin: 20px 0;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        select, input[type="text"] {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💰 Budget Transaction Categorizer</h1>
        
        <div class="upload-section">
            <h3>Step 1: Upload Your Bank CSV</h3>
            <input type="file" id="csvFile" accept=".csv">
            <button class="button" onclick="uploadAndProcess()">Upload & Categorize</button>
            <div id="uploadStatus" class="status"></div>
        </div>

        <div class="upload-section">
        <h3>Quick Add Transaction</h3>

        <input type="date" id="manualDate">
        <input type="text" id="manualDesc" placeholder="Description">
        <input type="number" id="manualAmount" step="0.01" placeholder="-25.00">
        <input type="text" id="manualCategory" placeholder="Category">

        <button class="button" onclick="addManualTransaction()">
            Add Transaction
        </button>

        <div id="manualStatus" class="status"></div>
        </div>

        <div id="upload-status" style="margin-top: 1em; font-family: monospace;"></div>
        
        <div id="statsSection" style="display:none;">
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-label">Total Transactions</div>
                    <div class="stat-value" id="totalCount">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Uncategorized</div>
                    <div class="stat-value" id="uncategorizedCount">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Categories Used</div>
                    <div class="stat-value" id="categoryCount">0</div>
                </div>
            </div>
            
            <div class="filter-section">
                <label>Filter by category:</label>
                <select id="categoryFilter" onchange="filterTransactions()">
                    <option value="">All Categories</option>
                </select>
                <label>Search:</label>
                <input type="text" id="searchBox" placeholder="Search descriptions..." oninput="filterTransactions()">
            </div>
            
            <button class="button button-success" onclick="downloadResults()">Download Categorized CSV</button>
	  <button class="button button-success" onclick="downloadResults()">Download Categorized CSV</button>
	  <button class="button" onclick="loadFromDatabase()">Load from Database</button>
	  <button class="button" onclick="showStats()">View Statistics</button> 
        </div>
        
        <div id="transactionsTable"></div>
    </div>

    <script>
        let transactions = [];
        let allCategories = new Set();
        
        function showStatus(message, type) {
            const status = document.getElementById('uploadStatus');
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
        }
        
        async function uploadAndProcess() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];

    if (!file) {
        showStatus('Please select a CSV file first', 'error');
        return;
    }

    showStatus('Uploading and importing CSV into database…', 'info');

    const formData = new FormData();
    formData.append('file', file);

    try {
        // 1️⃣ Upload & normalize (DB insert)
        const normalizeResponse = await fetch('/normalize/csv', {
            method: 'POST',
            body: formData
        });

        const normalizeData = await normalizeResponse.json();

        if (!normalizeResponse.ok || !normalizeData.success) {
            showStatus('Upload failed', 'error');
            return;
        }

        showStatus(
            `✓ Upload complete. Inserted ${normalizeData.inserted}, skipped ${normalizeData.skipped}. Categorizing…`,
            'info'
        );

        // 2️⃣ Trigger categorization (background)
        const catResp = await fetch('/categorize/pending', { method: 'POST' });
        const catData = await catResp.json();

        // 3️⃣ Reload from DB (source of truth)
        const loadResp = await fetch('/transactions/from-db');
        const dbData = await loadResp.json();

        transactions = dbData.transactions;

        updateCategories();
        displayTransactions();
        document.getElementById('statsSection').style.display = 'block';

        showStatus(
            `✓ Ready. ${catData.updated ?? 0} categorized.`,
            'success'
        );

    } catch (error) {
        showStatus('Error: ' + error.message, 'error');
    }
}

        
        function updateCategories() {
            allCategories.clear();
            transactions.forEach(t => {
                if (t.category) allCategories.add(t.category);
            });
            
            const filterSelect = document.getElementById('categoryFilter');
            filterSelect.innerHTML = '<option value="">All Categories</option>';
            Array.from(allCategories).sort().forEach(cat => {
                filterSelect.innerHTML += `<option value="${cat}">${cat}</option>`;
            });
            
            document.getElementById('totalCount').textContent = transactions.length;
            document.getElementById('uncategorizedCount').textContent = 
                transactions.filter(t => !t.category || t.category.startsWith('Uncategorized')).length;
            document.getElementById('categoryCount').textContent = allCategories.size;
        }
        
        function displayTransactions(filtered = null) {
            const data = filtered || transactions;
            
            let html = `
                <table>
                    <thead>
                        <tr>
                            <th style="width: 50px;">#</th>
                            <th style="width: 100px;">Date</th>
                            <th>Description</th>
                            <th style="width: 100px;">Amount</th>
                            <th style="width: 250px;">Category</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            data.forEach((txn, idx) => {
                const originalIdx = transactions.indexOf(txn);
                const amountClass = txn.amount >= 0 ? 'amount-positive' : 'amount-negative';
                const amountDisplay = txn.amount >= 0 ? `+$${txn.amount.toFixed(2)}` : `-$${Math.abs(txn.amount).toFixed(2)}`;
                
                html += `
                    <tr>
                        <td>${originalIdx}</td>
                        <td>${txn.date}</td>
                        <td>${txn.description}</td>
                        <td class="${amountClass}">${amountDisplay}</td>
                        <td>
                            <div class="category-cell">
                                <input 
                                    type="text" 
                                    class="category-input" 
                                    value="${txn.category || ''}" 
                                    list="categories-${originalIdx}"
                                    onchange="updateCategory(${txn.id}, this.value)"
                                    placeholder="Enter category">
                                <datalist id="categories-${originalIdx}">
                                    ${Array.from(allCategories).sort().map(cat => 
                                        `<option value="${cat}">`
                                    ).join('')}
                                </datalist>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            document.getElementById('transactionsTable').innerHTML = html;
        }
        
async function updateCategory(transactionId, newCategory) {
  try {
    const response = await fetch(
      `/transactions/${transactionId}/category?category=${encodeURIComponent(newCategory)}`,
      { method: 'PUT' }
    );

    if (!response.ok) {
      throw new Error('Failed to update category');
    }

    showStatus('Category updated', 'success');
  } catch (error) {
    showStatus('Error updating category: ' + error.message, 'error');
  }
}



async function loadFromDatabase() {
    try {
        showStatus('Loading from database...', 'info');
        const response = await fetch('/transactions/from-db');
        const data = await response.json();
        
        transactions = data.transactions;
        updateCategories();
        displayTransactions();
        document.getElementById('statsSection').style.display = 'block';
        
        showStatus(`✓ Loaded ${data.transaction_count} transactions from database`, 'success');
    } catch (error) {
        showStatus('Error loading: ' + error.message, 'error');
    }
}

async function addManualTransaction() {
  const body = {
    date: document.getElementById('manualDate').value,
    description: document.getElementById('manualDesc').value,
    amount: parseFloat(document.getElementById('manualAmount').value),
    category: document.getElementById('manualCategory').value
  };

  const res = await fetch('/transactions/manual', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (res.ok) {
    showStatus('Transaction added', 'success');
  } else {
    showStatus('Failed to add transaction', 'error');
  }
}

async function showStats() {
    try {
        const response = await fetch('/transactions/stats');
        const stats = await response.json();
        
        let message = `📊 Statistics:\\n\\n`;
        message += `Total Transactions: ${stats.overall.total_transactions}\\n`;
        message += `Total Spent: $${Math.abs(stats.overall.total_spent).toFixed(2)}\\n`;
        message += `Total Income: $${stats.overall.total_income.toFixed(2)}\\n`;
        message += `Date Range: ${stats.overall.date_range}\\n\\n`;
        message += `Top Spending Categories:\\n`;
        
        stats.by_category
            .filter(c => c.total < 0)
            .sort((a, b) => a.total - b.total)
            .slice(0, 5)
            .forEach(cat => {
                message += `  ${cat.category}: $${Math.abs(cat.total).toFixed(2)} (${cat.count} transactions)\\n`;
            });
        
        alert(message);
    } catch (error) {
        showStatus('Error getting stats: ' + error.message, 'error');
    }
}
    </script>
</body>
</html>
    """
@app.post("/transactions/{transaction_id}/category")
def update_transaction_category(
    transaction_id: int,
    update: CategoryUpdate
):
    with duckdb.connect(DB_PATH) as con:
        result = con.execute(
            """
            UPDATE transactions
            SET category = ?
            WHERE id = ?
            RETURNING id, category
            """,
            [update.category, transaction_id]
        ).fetchone()

    if result is None:
        return {"error": "Transaction not found"}

    return {
        "id": result[0],
        "category": result[1],
        "status": "updated"
    }

@app.put("/transactions/{transaction_id}/category")
def update_transaction_category(transaction_id: int, category: str):
    conn = get_db()

    result = conn.execute("""
        UPDATE transactions
        SET category = ?
        WHERE id = ?
    """, [category, transaction_id])

    conn.close()

    return {"success": True}
from fastapi.responses import HTMLResponse

@app.get("/rules", response_class=HTMLResponse)
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
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.templating import Jinja2Templates
from datetime import date

templates = Jinja2Templates(directory="templates")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = get_db()

    # Current balance
    result = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) FROM transactions
    """).fetchone()

    current_balance = result[0]

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
            "monthly_expenses": monthly_expenses,
            "monthly_net": monthly_net,
            "categories": categories,
            "transactions": transactions,
            "category_labels": category_labels,
            "recent_transactions": recent_transactions,
            "category_totals": category_totals
        }
    )


@app.post("/add-transaction")
def add_transaction(
    date: str = Form(...),
    description: str = Form(...),
    amount: float = Form(...),
    category: str = Form(None)
):
    conn = get_db()

    conn.execute("""
        INSERT INTO transactions (date, description, amount, category, source)
        VALUES (?, ?, ?, ?, 'manual')
    """, (date, description, amount, category or "Uncategorized"))

    conn.commit()

    return RedirectResponse(url="/dashboard", status_code=303)
