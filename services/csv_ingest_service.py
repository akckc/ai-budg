import csv
import io
from utils.money import parse_money
from utils.dates import normalize_date
from repositories.transactions_repository import (
    transaction_exists,
    insert_transaction,
)

REQUIRED_COLUMNS = {"Date", "Description", "Amount", "Balance"}


def ingest_csv(contents: str):
    reader = csv.DictReader(io.StringIO(contents, newline=""))

    if not reader.fieldnames:
        return {"success": False, "error": "CSV is missing headers"}

    missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
    if missing:
        return {
            "success": False,
            "error": f"CSV is missing required columns: {', '.join(missing)}"
        }

    inserted = 0
    skipped = 0
    invalid = 0

    for row in reader:
        try:
            raw_date = (row.get("Date") or "").strip()
            raw_description = (row.get("Description") or "").strip()

            if not raw_date or not raw_description:
                raise ValueError

            date = normalize_date(raw_date)
            amount = parse_money(row.get("Amount"))
            balance = parse_money(row.get("Balance"))

        except Exception:
            invalid += 1
            continue

        if transaction_exists(date, raw_description, amount, balance):
            skipped += 1
            continue

        insert_transaction(date, raw_description, amount, balance)
        inserted += 1

    return {
        "success": True,
        "inserted": inserted,
        "skipped": skipped,
        "invalid": invalid
    }