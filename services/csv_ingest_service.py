import csv
import io
import logging
from duckdb import IntegrityError
from db import get_db  # <-- use the new helper
from repositories.transactions_repository import insert_transaction
from utils.money import parse_money
from utils.dates import normalize_date

REQUIRED_COLUMNS = {"Date", "Description", "Amount", "Balance"}

logging.basicConfig(
    filename="csv_ingest.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def ingest_csv(contents: str):
    reader = csv.DictReader(io.StringIO(contents, newline=""))
    if not reader.fieldnames:
        return {"success": False, "error": "CSV is missing headers"}

    missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
    if missing:
        return {"success": False, "error": f"CSV is missing required columns: {', '.join(missing)}"}

    results = []

    conn = get_db()  # open a connection to pass to repository functions if needed

    for idx, row in enumerate(reader, start=1):
        row_result = {"row": idx, "success": False, "error": None}

        try:
            raw_date = (row.get("Date") or "").strip()
            raw_description = (row.get("Description") or "").strip()
            if not raw_date or not raw_description:
                raise ValueError("Missing required date or description")

            date = normalize_date(raw_date)
            description = raw_description
            amount = parse_money(row.get("Amount"))
            balance = parse_money(row.get("Balance")) if row.get("Balance") else None
            category = row.get("Category") or None
            source = row.get("Source") or "unknown"
            user_id = row.get("User ID") or None
            merchant_id = row.get("Merchant ID") or None
            account_name = row.get("Account Name")  # optional, repository handles mapping

            # Insert transaction via repository (pass conn if repo supports it)
            insert_transaction(
                conn=conn,
                account_name=account_name,
                date=date,
                description=description,
                amount=amount,
                balance=balance,
                category=category,
                source=source,
                user_id=user_id,
                merchant_id=merchant_id
            )

            row_result["success"] = True

        except IntegrityError:
            row_result["error"] = "Duplicate transaction (unique constraint)"
        except Exception as e:
            row_result["error"] = str(e)

        results.append(row_result)
        if row_result["success"]:
            logging.info(f"Row {idx} inserted successfully (account={account_name or 'Primary Account'})")
        else:
            logging.warning(f"Row {idx} failed: {row_result['error']}")

    conn.close()  # close the connection after ingestion

    return {
        "success": True,
        "inserted": sum(r["success"] for r in results),
        "failed": [r for r in results if not r["success"]],
        "total": len(results)
    }