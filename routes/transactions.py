import csv
import io

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from services.transaction_service import (
    get_all_transactions,
    update_transaction_category,
    reclassify_all_transactions,
    get_filtered_transactions,
    get_transactions_for_export,
    delete_transactions,
    link_transaction_to_recurring,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class LinkRecurringRequest(BaseModel):
    recurring_event_id: int | None = None

# Standard allowed categories for dropdown
ALLOWED_CATEGORIES = [
    "Car Insurance",
    "Car Payment",
    "Car Repairs/Maintenance",
    "Clothing",
    "Credit Cards",
    "Gas",
    "Groceries",
    "Health/Fitness",
    "Home Improvement",
    "Household",
    "Income",
    "Life Insurance",
    "Medical/Prescriptions",
    "Mortgage",
    "Pet Care",
    "Restaurant",
    "Student Loans",
    "Subscriptions",
    "Taxes",
    "Transfer",
    "Utilities",
]


# -------------------------
# READ TRANSACTIONS
# -------------------------

@router.get("/transactions/from-db")
def get_transactions_from_db():
    transactions = get_all_transactions()
    # Convert tuples to dicts for consistent JSON response
    tx_dicts = [
        {
            "id": t[0],
            "account_name": t[1],
            "date": t[2],
            "description": t[3],
            "amount": t[4],
            "balance": t[5],
            "category": t[6],
            "source": t[7],
            "user_id": t[8],
            "merchant_id": t[9],
            "merchant_normalized": t[10],
            "created_at": t[11],
        }
        for t in transactions
    ]
    return {"transactions": tx_dicts}


@router.get("/transactions")
def get_transactions(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    account_id: Optional[int] = None,
):
    """Render transactions page with inline category editing."""
    if start_date is None and end_date is None and category is None and account_id is None:
        transactions = get_all_transactions()
        # Convert tuples to dicts for template rendering
        tx_dicts = [
            {
                "id": t[0],
                "account_name": t[1],
                "date": t[2],
                "description": t[3],
                "amount": t[4],
                "balance": t[5],
                "category": t[6] if t[6] else "",
                "source": t[7],
                "user_id": t[8],
                "merchant_id": t[9],
                "merchant_normalized": t[10],
                "created_at": t[11],
            }
            for t in transactions
        ]
    else:
        tx_dicts = get_filtered_transactions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            account_id=account_id,
        )

    return templates.TemplateResponse(
        request,
        "transactions.html",
        {
            "transactions": tx_dicts,
            "allowed_categories": ALLOWED_CATEGORIES,
        },
    )


@router.get("/transactions/export")
def export_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    account_id: Optional[int] = None,
):
    """Stream a CSV download of transactions, optionally filtered.

    With no query params, exports all transactions.
    """
    transactions = get_transactions_for_export(
        start_date=start_date,
        end_date=end_date,
        category=category,
        account_id=account_id,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "description", "amount", "category", "source"])
    for tx in transactions:
        writer.writerow([
            tx["date"],
            tx["description"],
            tx["amount"],
            tx["category"] or "",
            tx["source"],
        ])

    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    return StreamingResponse(
        csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transactions-export.csv"'},
    )


# -------------------------
# UPDATE CATEGORY
# -------------------------

@router.put("/transactions/{transaction_id}/category")
def update_category(transaction_id: int, category: str):
    update_transaction_category(transaction_id, category)
    return {"success": True}


# -------------------------
# RECLASSIFY TRANSACTIONS
# -------------------------

@router.post("/transactions/reclassify")
def reclassify():
    """Re-apply category rules to all transactions deterministically.

    Returns count of transactions updated.
    """
    updated_count = reclassify_all_transactions()
    return {"success": True, "updated": updated_count}


# -------------------------
# DELETE TRANSACTIONS
# -------------------------

@router.post("/transactions/{transaction_id}/link_recurring")
def link_recurring(transaction_id: int, payload: LinkRecurringRequest):
    link_transaction_to_recurring(
        transaction_id=transaction_id,
        recurring_event_id=payload.recurring_event_id,
    )
    return {"success": True}


@router.post("/transactions/delete")
async def delete_selected_transactions(request: Request):
    """Delete transactions by ID.

    Accepts JSON body: ``{"transaction_ids": [1, 2, 3]}``
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "error": "Invalid JSON in request body"}
    transaction_ids = data.get("transaction_ids", [])

    if not transaction_ids:
        return {"status": "error", "error": "No transactions selected"}

    # Validate all IDs are integers
    try:
        transaction_ids = [int(tid) for tid in transaction_ids]
    except (ValueError, TypeError):
        return {"status": "error", "error": "Invalid transaction IDs"}

    try:
        deleted_count = delete_transactions(transaction_ids)
        return {"status": "success", "deleted_count": deleted_count}
    except Exception as e:
        return {"status": "error", "error": str(e)}
