from datetime import datetime

def normalize_date(raw_date: str) -> str:
    date_obj = datetime.strptime(raw_date, "%m/%d/%Y")
    return date_obj.strftime("%Y-%m-%d")