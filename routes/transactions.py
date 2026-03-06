from fastapi import APIRouter
from typing import Optional

from services.transaction_service import (
    get_all_transactions,
    update_transaction_category,
    reclassify_all_transactions,
    get_filtered_transactions,
)

router = APIRouter()


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
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    account_id: Optional[int] = None,
):
    if start_date is None and end_date is None and category is None and account_id is None:
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

    return {
        "transactions": get_filtered_transactions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            account_id=account_id,
        )
    }


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