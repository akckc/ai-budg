from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import csv
import io
from services.csv_ingest_service import ingest_csv
from services.reconciliation_service import initiate_reconciliation
from repositories.accounts_repository import get_or_create_account, list_accounts
from routes.reconciliation import store_reconciliation_session
from utils.money import parse_money
from utils.dates import normalize_date

router = APIRouter()

_COMMON_STYLES = """
    <style>
        :root {
            --bg-main: #2F2F2F;
            --bg-card: #3A3A3A;
            --bg-card-hover: #444444;
            --border-default: #505050;
            --text-primary: #F2F2F2;
            --text-secondary: #C8C8C8;
            --text-muted: #9A9A9A;
            --color-income: #3FB950;
            --color-expense: #F85149;
            --color-budget: #58A6FF;
            --color-warning: #F2CC60;
        }

        body {
            font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            padding: 32px;
            background: var(--bg-main);
            color: var(--text-primary);
            margin: 0;
        }

        h1 {
            font-size: 28px;
            margin: 0 0 32px 0;
            color: var(--text-primary);
        }

        h2 {
            font-size: 16px;
            margin: 24px 0 16px 0;
            color: var(--text-primary);
            font-weight: 600;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-default);
            border-radius: 8px;
            padding: 16px;
            max-width: 500px;
            margin-bottom: 24px;
        }

        label {
            display: block;
            color: var(--text-secondary);
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        input[type="file"],
        input[type="text"],
        select {
            display: block;
            width: 100%;
            padding: 10px 12px;
            background: var(--bg-main);
            border: 1px solid var(--border-default);
            border-radius: 6px;
            color: var(--text-primary);
            margin-bottom: 16px;
            font-size: 14px;
            box-sizing: border-box;
        }

        input[type="file"] {
            border-style: dashed;
            border-width: 2px;
            cursor: pointer;
        }

        input[type="file"]:hover {
            border-color: var(--color-budget);
            background: rgba(88, 166, 255, 0.05);
        }

        select {
            cursor: pointer;
        }

        select option {
            background: var(--bg-card);
        }

        button {
            padding: 8px 14px;
            cursor: pointer;
            background: var(--color-budget);
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 14px;
            transition: background 0.2s;
            width: 100%;
        }

        button:hover {
            background: #6CB6FF;
        }

        button:disabled {
            background: var(--text-muted);
            cursor: not-allowed;
        }

        p {
            color: var(--text-primary);
            line-height: 1.5;
            margin: 8px 0;
        }

        .success {
            background: rgba(63, 185, 80, 0.1);
            border: 1px solid var(--color-income);
            color: var(--color-income);
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 16px;
            font-size: 15px;
        }

        .error {
            background: rgba(248, 81, 73, 0.1);
            border: 1px solid var(--color-expense);
            color: var(--color-expense);
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 16px;
            font-size: 15px;
        }

        .info {
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 12px;
            line-height: 1.6;
        }

        a {
            color: var(--color-budget);
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .back-link {
            display: inline-block;
            margin-bottom: 24px;
        }
    </style>
"""


@router.get("/upload", response_class=HTMLResponse)
def upload_page():
    accounts = list_accounts()

    account_options = '<option value="">— Select Account —</option>\n'
    for acc in accounts:
        account_options += f'        <option value="{acc["id"]}">{acc["account_name"]}</option>\n'
    account_options += '        <option value="__new__">+ New Account…</option>\n'

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Upload CSV</title>
    {_COMMON_STYLES}
</head>
<body>
    <h1>Upload CSV</h1>
    <a class="back-link" href="/dashboard">← Back to Dashboard</a>

    <div class="card">
        <h2>Upload Transaction File</h2>
        <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
            <label for="accountSelect">Account</label>
            <select id="accountSelect" name="account_id">
                {account_options}
            </select>

            <div id="newAccountWrap" style="display:none;">
                <label for="newAccountName">New Account Name</label>
                <input type="text" id="newAccountName" name="new_account_name"
                       placeholder="e.g. Savings, Checking…">
            </div>

            <label for="csvFile">Select CSV File</label>
            <input type="file" id="csvFile" name="file" accept=".csv" required>

            <button type="submit" id="submitBtn">Upload</button>

            <div class="info">
                <strong>Expected CSV Format:</strong><br>
                Date, Description, Amount, Balance, Category<br>
                <em>Dates should be in YYYY-MM-DD format.</em>
            </div>
        </form>
    </div>

    <script>
        document.getElementById('accountSelect').addEventListener('change', function () {{
            var wrap = document.getElementById('newAccountWrap');
            var input = document.getElementById('newAccountName');
            if (this.value === '__new__') {{
                wrap.style.display = 'block';
                input.required = true;
            }} else {{
                wrap.style.display = 'none';
                input.required = false;
                input.value = '';
            }}
        }});
    </script>
</body>
</html>"""


@router.post("/upload", response_class=HTMLResponse)
def upload_csv(
    file: UploadFile = File(...),
    account_id: Optional[str] = Form(None),
    new_account_name: Optional[str] = Form(None),
):
    # Resolve account
    resolved_account_id = None
    if account_id == "__new__":
        if new_account_name and new_account_name.strip():
            account = get_or_create_account(new_account_name.strip())
            resolved_account_id = account["id"]
        # else fall through → ingest_csv will use account from CSV or Primary Account
    elif account_id and account_id.isdigit():
        resolved_account_id = int(account_id)

    contents_bytes = file.file.read()
    try:
        contents = contents_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return _error_page("File must be UTF-8 encoded CSV", None)

    # Parse CSV to check format
    csv_rows, parse_error = _parse_csv_rows(contents)
    if parse_error:
        return _error_page(parse_error["message"], parse_error.get("row"))

    # If resolved_account_id is available and we have manual transactions, use reconciliation workflow
    USE_RECONCILIATION = True  # Feature flag - set to False to use old ingest workflow
    
    if USE_RECONCILIATION and resolved_account_id and csv_rows:
        try:
            # Initiate reconciliation (fuzzy matching with existing manual entries)
            reconciliation_result = initiate_reconciliation(resolved_account_id, csv_rows)
            session_id = reconciliation_result["session_id"]
            
            # Store session data for review page
            store_reconciliation_session(session_id, {
                "account_id": resolved_account_id,
                "auto_matched": reconciliation_result["auto_matched"],
                "review_matches": reconciliation_result["review_matches"],
                "unmatched_csv": reconciliation_result["unmatched_csv"],
                "unmatched_manual": reconciliation_result["unmatched_manual"],
                "csv_rows": reconciliation_result["csv_rows"],
                "manual_entries": reconciliation_result["manual_entries"],
            })
            
            # Redirect to reconciliation review page
            return RedirectResponse(
                url=f"/reconciliation/review?session_id={session_id}",
                status_code=303
            )
        except Exception as e:
            # Fall back to old workflow if reconciliation fails
            return _error_page(f"Reconciliation failed: {str(e)}", None)
    
    # Fall back to old direct ingestion workflow
    result = ingest_csv(contents, account_id=resolved_account_id)

    if not result["success"]:
        return _error_page(result["error_message"], result["error_row"])

    if result["error_message"]:
        # Partial success: some rows imported, some failed
        return _partial_success_page(result["rows_imported"], result["error_message"], result["error_row"])

    return _success_page(result["rows_imported"], result["categories_assigned"])


def _parse_csv_rows(contents: str):
    """Parse CSV contents into rows for reconciliation. Returns (rows, error)."""
    REQUIRED_COLUMNS = {"Date", "Description", "Amount"}
    
    reader = csv.DictReader(io.StringIO(contents, newline=""))
    if not reader.fieldnames:
        return None, {"message": "CSV is missing headers", "row": None}

    missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
    if missing:
        return None, {"message": f"CSV is missing required columns: {', '.join(missing)}", "row": None}

    rows = []
    for idx, row in enumerate(reader, start=1):
        try:
            raw_date = (row.get("Date") or "").strip()
            raw_description = (row.get("Description") or "").strip()
            if not raw_date or not raw_description:
                return None, {"message": "Missing required date or description", "row": idx}

            date = normalize_date(raw_date)
            description = raw_description
            amount = parse_money(row.get("Amount"))
            balance = parse_money(row.get("Balance")) if row.get("Balance") else None
            category = row.get("Category") or None

            rows.append({
                "date": date,
                "description": description,
                "amount": amount,
                "balance": balance,
                "category": category,
            })
        except Exception as e:
            return None, {"message": str(e), "row": idx}

    return rows, None


def _success_page(rows_imported: int, categories_assigned: dict) -> str:
    cat_lines = ""
    if categories_assigned:
        cat_lines = "<ul style='margin:8px 0 0 0; padding-left:20px;'>"
        for cat, count in sorted(categories_assigned.items()):
            cat_lines += f"<li>{cat}: {count} row{'s' if count != 1 else ''}</li>"
        cat_lines += "</ul>"

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Upload Successful</title>
    {_COMMON_STYLES}
</head>
<body>
    <h1>Upload Complete</h1>
    <a class="back-link" href="/upload">← Upload Another File</a>

    <div class="card">
        <div class="success">
            <strong>✓ {rows_imported} row{'s' if rows_imported != 1 else ''} imported successfully</strong>
            {cat_lines}
        </div>
        <a href="/dashboard">→ Go to Dashboard</a>
    </div>
</body>
</html>"""


def _partial_success_page(rows_imported: int, error_message: str, error_row) -> str:
    row_info = f" (row {error_row})" if error_row is not None else ""
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Upload Partial Success</title>
    {_COMMON_STYLES}
</head>
<body>
    <h1>Upload Complete</h1>
    <a class="back-link" href="/upload">← Upload Another File</a>

    <div class="card">
        <div class="success">
            <strong>✓ {rows_imported} row{'s' if rows_imported != 1 else ''} imported successfully</strong>
        </div>
        <div class="error">
            <strong>⚠ Some rows were skipped</strong><br>
            {error_message}{row_info}
        </div>
        <a href="/dashboard">→ Go to Dashboard</a>
    </div>
</body>
</html>"""


def _error_page(error_message: str, error_row) -> str:
    row_info = f" (row {error_row})" if error_row is not None else ""
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html>
<head>
    <title>Upload Failed</title>
    {_COMMON_STYLES}
</head>
<body>
    <h1>Upload Failed</h1>
    <a class="back-link" href="/upload">← Try Again</a>

    <div class="card">
        <div class="error">
            <strong>✗ Import failed</strong><br>
            {error_message}{row_info}
        </div>
        <a href="/dashboard">→ Go to Dashboard</a>
    </div>
</body>
</html>""",
        status_code=422,
    )