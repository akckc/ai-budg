from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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
    contents_bytes = file.file.read()

    try:
        contents = contents_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "File must be UTF-8 encoded CSV"
        }

    reader = csv.DictReader(io.StringIO(contents, newline=""))

    required_columns = {"Date", "Description", "Amount", "Balance"}
    if not reader.fieldnames:
        return {
            "success": False,
            "error": "CSV is missing headers"
        }

    missing_columns = sorted(required_columns - set(reader.fieldnames))
    if missing_columns:
        return {
            "success": False,
            "error": f"CSV is missing required columns: {', '.join(missing_columns)}"
        }

    conn = get_db()

    inserted = 0
    skipped = 0
    invalid = 0

    def parse_money(value: str):
        if value is None:
            raise ValueError("missing money value")

        normalized = value.strip()
        if not normalized:
            raise ValueError("empty money value")

        is_negative = normalized.startswith("(") and normalized.endswith(")")
        normalized = normalized.replace("$", "").replace(",", "")

        if is_negative:
            normalized = normalized[1:-1]

        try:
            amount = Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation as exc:
            raise ValueError("invalid money value") from exc

        return -amount if is_negative else amount

    for row in reader:
        try:
            raw_date = (row.get("Date") or "").strip()
            raw_description = (row.get("Description") or "").strip()
            raw_amount = row.get("Amount")
            raw_balance = row.get("Balance")

            if not raw_date or not raw_description:
                raise ValueError("missing required row values")

            # Normalize
            date_obj = datetime.strptime(raw_date, "%m/%d/%Y")
            iso_date = date_obj.strftime("%Y-%m-%d")

            amount = parse_money(raw_amount)
            balance = parse_money(raw_balance)
            description = raw_description
        except (ValueError, TypeError):
            invalid += 1
            continue

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
        "skipped": skipped,
        "invalid": invalid
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
