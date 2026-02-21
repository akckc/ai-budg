from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
import csv
import io
from datetime import datetime
from db import get_db

router = APIRouter()


# -------------------------
# SIMPLE UPLOAD PAGE
# -------------------------

@router.get("/upload", response_class=HTMLResponse)
def upload_page():
    return """
    <html>
        <body style="font-family: Arial; padding: 40px;">
            <h2>Upload Bank CSV</h2>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".csv" required>
                <button type="submit">Upload</button>
            </form>
            <br>
            <a href="/dashboard">Back to Dashboard</a>
        </body>
    </html>
    """


# -------------------------
# CSV INGESTION
# -------------------------

@router.post("/upload")
def upload_csv(file: UploadFile = File(...)):
    contents = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(contents))

    conn = get_db()

    inserted = 0
    skipped = 0

    for row in reader:

        # Normalize
        date_obj = datetime.strptime(row["Date"], "%m/%d/%Y")
        iso_date = date_obj.strftime("%Y-%m-%d")

        amount = float(row["Amount"].replace("$", "").replace(",", ""))

        description = row["Description"].strip()
        balance = float(row["Balance"].replace("$", "").replace(",", ""))

        # Deduplicate
        exists = conn.execute("""
            SELECT 1 FROM transactions
            WHERE date = ?
              AND description = ?
              AND amount = ?
              AND balance = ?
        """, [iso_date, description, amount, balance]).fetchone()

        if exists:
            skipped += 1
            continue

        conn.execute("""
            INSERT INTO transactions
            (date, description, amount, balance, category, source)
            VALUES (?, ?, ?, ?, NULL, 'csv')
        """, [iso_date, description, amount, balance])

        inserted += 1

    conn.close()

    return {
        "success": True,
        "inserted": inserted,
        "skipped": skipped
    }


# -------------------------
# READ TRANSACTIONS
# -------------------------

@router.get("/transactions/from-db")
def get_transactions_from_db():
    conn = get_db()

    result = conn.execute("""
        SELECT id, date, description, amount, balance, category
        FROM transactions
        ORDER BY date DESC
    """).fetchall()

    conn.close()

    return {"transactions": result}


# -------------------------
# UPDATE CATEGORY
# -------------------------

@router.put("/transactions/{transaction_id}/category")
def update_transaction_category(transaction_id: int, category: str):
    conn = get_db()

    conn.execute("""
        UPDATE transactions
        SET category = ?
        WHERE id = ?
    """, [category, transaction_id])

    conn.close()

    return {"success": True}