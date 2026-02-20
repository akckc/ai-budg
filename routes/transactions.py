from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse
from db import get_db

router = APIRouter()

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

    return RedirectResponse(url="/dashboard", status_code=303)

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
from fastapi.responses import HTMLResponse

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

    return RedirectResponse(url="/dashboard", status_code=303)