from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse

from services.csv_ingest_service import ingest_csv
from services.transaction_service import (
    get_all_transactions,
    update_transaction_category,
)

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