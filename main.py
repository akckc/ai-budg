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
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Budget Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            color: #6c757d;
            font-size: 14px;
        }
        
        .header .actions {
            margin-top: 15px;
        }
        
        .button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
            display: inline-block;
            margin-right: 10px;
        }
        
        .button:hover {
            background: #5568d3;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .metric-label {
            font-size: 14px;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }
        
        .metric-value {
            font-size: 36px;
            font-weight: 700;
            color: #333;
        }
        
        .metric-value.positive {
            color: #28a745;
        }
        
        .metric-value.negative {
            color: #dc3545;
        }
        
        .metric-change {
            font-size: 12px;
            color: #6c757d;
            margin-top: 5px;
        }
        
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
        }
        
        .category-bar {
            margin-bottom: 15px;
        }
        
        .category-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 14px;
        }
        
        .category-name {
            font-weight: 500;
            color: #495057;
        }
        
        .category-amount {
            font-weight: 600;
            color: #dc3545;
        }
        
        .category-bar-fill {
            height: 30px;
            background: linear-gradient(90deg, #dc3545 0%, #c82333 100%);
            border-radius: 6px;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            padding: 0 10px;
            color: white;
            font-size: 12px;
            font-weight: 600;
        }
        
        .burndown-chart {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        
        canvas {
            max-width: 100%;
        }
        
        .loading {
            text-align: center;
            padding: 60px;
            color: white;
            font-size: 18px;
        }
        
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .no-data {
            background: white;
            border-radius: 12px;
            padding: 60px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .no-data h2 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .no-data p {
            color: #6c757d;
            margin-bottom: 20px;
        }
        
        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        @media (max-width: 768px) {
            .two-column {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 Budget Dashboard</h1>
            <p class="subtitle" id="lastUpdated">Loading...</p>
            <div class="actions">
                <button class="button" onclick="loadDashboard()">🔄 Refresh</button>
                <a href="/upload" class="button">📤 Upload Transactions</a>
            </div>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Loading your financial data...</p>
        </div>
        
        <div id="dashboard" style="display:none;">
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Current Balance</div>
                    <div class="metric-value" id="currentBalance">$0.00</div>
                    <div class="metric-change" id="balanceChange"></div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Total Spent (This Period)</div>
                    <div class="metric-value negative" id="totalSpent">$0.00</div>
                    <div class="metric-change" id="spentTransactions"></div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Total Income (This Period)</div>
                    <div class="metric-value positive" id="totalIncome">$0.00</div>
                    <div class="metric-change" id="incomeTransactions"></div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Net Cash Flow</div>
                    <div class="metric-value" id="netFlow">$0.00</div>
                    <div class="metric-change" id="flowChange"></div>
                </div>
            </div>
            
            <div class="two-column">
                <div class="chart-container">
                    <div class="chart-title">💳 Spending by Category</div>
                    <div id="categoryBars"></div>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title">📊 Top Expenses</div>
                    <div id="topExpenses"></div>
                </div>
            </div>
            
            <div class="chart-container">
                <div class="chart-title">📈 Balance Over Time</div>
                <canvas id="burndownChart"></canvas>
            </div>
        </div>
        
        <div id="noData" class="no-data" style="display:none;">
            <h2>No Data Available</h2>
            <p>Upload your first CSV to get started!</p>
            <a href="/upload" class="button">📤 Upload Transactions</a>
        </div>
    </div>

    <script>
        let chartInstance = null;
        
        async function loadDashboard() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('dashboard').style.display = 'none';
            document.getElementById('noData').style.display = 'none';
            
            try {
                const [transactionsRes, statsRes] = await Promise.all([
                    fetch('/transactions/from-db'),
                    fetch('/transactions/stats')
                ]);
                
                const transactionsData = await transactionsRes.json();
                const statsData = await statsRes.json();
                
                if (transactionsData.transaction_count === 0) {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('noData').style.display = 'block';
                    return;
                }
                
                renderDashboard(transactionsData, statsData);
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('dashboard').style.display = 'block';
                
            } catch (error) {
                document.getElementById('loading').innerHTML = 
                    '<p style="color: white;">Error loading data: ' + error.message + '</p>';
            }
        }
        
        function renderDashboard(transactionsData, statsData) {
            const transactions = transactionsData.transactions;
            const stats = statsData.overall;
            
            // Update last updated time
            const latestDate = transactions[0]?.date || 'Unknown';
            document.getElementById('lastUpdated').textContent = 
                `Latest transaction: ${latestDate} • ${stats.total_transactions} total transactions`;
            
            // Current balance (from most recent transaction)
            const currentBalance = transactions[0]?.balance || 0;
            document.getElementById('currentBalance').textContent = 
                `$${currentBalance.toFixed(2)}`;
            document.getElementById('balanceChange').textContent = 
                `From ${stats.date_range}`;
            
            // Total spent
            document.getElementById('totalSpent').textContent = 
                `$${Math.abs(stats.total_spent).toFixed(2)}`;
            const spentCount = transactions.filter(t => t.amount < 0).length;
            document.getElementById('spentTransactions').textContent = 
                `${spentCount} transactions`;
            
            // Total income
            document.getElementById('totalIncome').textContent = 
                `$${stats.total_income.toFixed(2)}`;
            const incomeCount = transactions.filter(t => t.amount > 0).length;
            document.getElementById('incomeTransactions').textContent = 
                `${incomeCount} transactions`;
            
            // Net flow
            const netFlow = stats.total_income + stats.total_spent;
            const netFlowEl = document.getElementById('netFlow');
            netFlowEl.textContent = `$${Math.abs(netFlow).toFixed(2)}`;
            netFlowEl.className = 'metric-value ' + (netFlow >= 0 ? 'positive' : 'negative');
            document.getElementById('flowChange').textContent = 
                netFlow >= 0 ? 'Positive cash flow' : 'Negative cash flow';
            
            // Category spending bars
            renderCategoryBars(statsData.by_category);
            
            // Top expenses
            renderTopExpenses(transactions);
            
            // Burndown chart
            renderBurndownChart(transactions);
        }
        
        function renderCategoryBars(categories) {
            const spending = categories
                .filter(c => c.total < 0)
                .sort((a, b) => a.total - b.total)
                .slice(0, 8);
            
            const maxAmount = Math.abs(spending[0]?.total || 1);
            
            let html = '';
            spending.forEach(cat => {
                const percentage = (Math.abs(cat.total) / maxAmount) * 100;
                html += `
                    <div class="category-bar">
                        <div class="category-header">
                            <span class="category-name">${cat.category}</span>
                            <span class="category-amount">$${Math.abs(cat.total).toFixed(2)}</span>
                        </div>
                        <div class="category-bar-fill" style="width: ${percentage}%">
                            ${cat.count} transactions
                        </div>
                    </div>
                `;
            });
            
            document.getElementById('categoryBars').innerHTML = html || '<p>No spending data</p>';
        }
        
        function renderTopExpenses(transactions) {
            const expenses = transactions
                .filter(t => t.amount < 0)
                .sort((a, b) => a.amount - b.amount)
                .slice(0, 10);
            
            let html = '<div style="font-size: 14px;">';
            expenses.forEach((txn, idx) => {
                html += `
                    <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee;">
                        <div>
                            <div style="font-weight: 500;">${txn.description.substring(0, 50)}${txn.description.length > 50 ? '...' : ''}</div>
                            <div style="font-size: 12px; color: #6c757d;">${txn.date} • ${txn.category}</div>
                        </div>
                        <div style="font-weight: 600; color: #dc3545;">$${Math.abs(txn.amount).toFixed(2)}</div>
                    </div>
                `;
            });
            html += '</div>';
            
            document.getElementById('topExpenses').innerHTML = html;
        }
        
        function renderBurndownChart(transactions) {
            // Sort by date ascending
            const sorted = [...transactions].sort((a, b) => 
                new Date(a.date) - new Date(b.date)
            );
            
            const dates = sorted.map(t => t.date);
            const balances = sorted.map(t => t.balance);
            
            const ctx = document.getElementById('burndownChart').getContext('2d');
            
            if (chartInstance) {
                chartInstance.destroy();
            }
            
            chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Balance',
                        data: balances,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(0);
                                }
                            }
                        },
                        x: {
                            ticks: {
                                maxRotation: 45,
                                minRotation: 45
                            }
                        }
                    }
                }
            });
        }
        
        // Load dashboard on page load
        loadDashboard();
        
        // Auto-refresh every 5 minutes
        setInterval(loadDashboard, 5 * 60 * 1000);
    </script>
</body>
</html>
    """
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
    balance_row = conn.execute("""
        SELECT balance
        FROM transactions
        ORDER BY date DESC, id DESC
        LIMIT 1
    """).fetchone()

    current_balance = balance_row[0] if balance_row else 0

    # This month income
    income = conn.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE amount > 0
        AND date >= date_trunc('month', CURRENT_DATE)
    """).fetchone()[0]

    # This month expenses
    expenses = conn.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE amount < 0
        AND date >= date_trunc('month', CURRENT_DATE)
    """).fetchone()[0]

    # Spending by category
    categories = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE amount < 0
        AND date >= date_trunc('month', CURRENT_DATE)
        GROUP BY category
        ORDER BY total ASC
    """).fetchall()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "balance": round(current_balance, 2),
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "net": round(income + expenses, 2),
        "categories": categories
    })
