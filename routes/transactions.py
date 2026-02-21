from fastapi import APIRouter, Form,UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
import csv
import io
from datetime import datetime
from db import get_db

router = APIRouter()




@router.post("/transactions/manual")
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

@router.put("/transactions/{transaction_id}/category")
def update_transaction_category(transaction_id: int, category: str):
    conn = get_db()

    result = conn.execute("""
        UPDATE transactions
        SET category = ?
        WHERE id = ?
    """, [category, transaction_id])

    conn.close()

    return {"success": True}


@router.get("/transactions/from-db")
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

@router.get("/transactions/stats")
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

@router.post("/add-transaction")
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
    conn.close()

    return RedirectResponse(url="/dashboard", status_code=303)

@router.get("/upload", response_class=HTMLResponse)
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

@router.post("/upload/csv")
def upload_csv(file: UploadFile = File(...)):
    contents = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(contents))

    conn = get_db()

    inserted = 0
    skipped = 0

    for row in reader:
        #txn = normalize_row(row)  # ← your existing normalization logic

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


@router.post("/normalize/csv")
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