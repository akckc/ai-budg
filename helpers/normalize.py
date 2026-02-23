# helpers/normalize.py
from datetime import datetime

def normalize_row(row: dict, column_map: dict, account_name: str):
    """
    Convert a CSV row into canonical transaction dict
    """
    try:
        normalized = {
            "transaction_id": f"{account_name}_{row[column_map['date']]}_{row[column_map['amount']]}",
            "account_name": account_name,
            "date": datetime.strptime(row[column_map['date']], "%Y-%m-%d").date(),
            "description": row.get(column_map.get("description", ""), ""),
            "merchant": row.get(column_map.get("merchant", ""), ""),
            "category": None,  # default, to be assigned later
            "amount": float(row[column_map['amount']]),
            "currency": row.get(column_map.get("currency", "USD"), "USD"),
            "raw_data": row,
        }
        return normalized
    except Exception as e:
        # Could log or collect invalid rows
        return None, str(e)