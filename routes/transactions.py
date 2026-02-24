from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from services.csv_ingest_service import ingest_csv
from services.transaction_service import (
    get_all_transactions,
    update_transaction_category,
)
from repositories.accounts_repository import get_or_create_account
from repositories.transactions_repository import insert_transaction

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

    return ingest_csv(contents)


# -------------------------
# READ TRANSACTIONS
# -------------------------

@router.get("/transactions/from-db")
def get_transactions_from_db():
    return {"transactions": get_all_transactions()}


# -------------------------
# UPDATE CATEGORY
# -------------------------

@router.put("/transactions/{transaction_id}/category")
def update_category(transaction_id: int, category: str):
    update_transaction_category(transaction_id, category)
    return {"success": True}


# -------------------------
# MANUAL TRANSACTION ADD
# -------------------------

class ManualTransaction(BaseModel):
    account_name: str
    date: str  # ISO format YYYY-MM-DD
    description: str
    amount: float
    balance: Optional[float] = None
    category: Optional[str] = None
    source: Optional[str] = "Manual"


@router.post("/transactions/manual")
def add_manual_transaction(tx: ManualTransaction):
    # Ensure account exists (multi-account support)
    account = get_or_create_account(tx.account_name)
    account_id = account["id"]

    try:
        insert_transaction(
            account_id=account_id,
            date=tx.date,
            description=tx.description,
            amount=tx.amount,
            balance=tx.balance,
            category=tx.category,
            source=tx.source,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Insert failed: {e}")

    return {"success": True, "message": "Transaction added"}