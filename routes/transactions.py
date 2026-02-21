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