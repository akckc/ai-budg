from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from services.reconciliation_service import apply_reconciliation
from typing import Optional
import json
import logging

# Add logging
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Temporary in-memory storage for reconciliation session data
# In production, this would be stored in Redis or a session table
_reconciliation_sessions = {}


@router.get("/reconciliation/review", response_class=HTMLResponse)
def reconciliation_review_page(request: Request, session_id: str):
    """
    Display reconciliation review page with matched/unmatched transactions.
    """
    if session_id not in _reconciliation_sessions:
        return HTMLResponse(
            content="<h1>Session not found</h1><p>Reconciliation session expired or invalid.</p>",
            status_code=404
        )
    
    data = _reconciliation_sessions[session_id]
    
    # Prepare display data
    csv_rows = data['csv_rows']
    manual_entries = data['manual_entries']
    
    # Build lookup maps
    manual_map = {m['id']: m for m in manual_entries}
    
    auto_matched_display = []
    for csv_idx, manual_id, score in data['auto_matched']:
        auto_matched_display.append({
            'csv_idx': csv_idx,
            'manual_id': manual_id,
            'score': round(score, 1),
            'csv_row': csv_rows[csv_idx],
            'manual_entry': manual_map.get(manual_id, {})
        })
    
    review_matches_display = []
    for csv_idx, manual_id, score in data['review_matches']:
        review_matches_display.append({
            'csv_idx': csv_idx,
            'manual_id': manual_id,
            'score': round(score, 1),
            'csv_row': csv_rows[csv_idx],
            'manual_entry': manual_map.get(manual_id, {})
        })
    
    unmatched_csv_display = [
        {'csv_idx': idx, 'csv_row': csv_rows[idx]}
        for idx in data['unmatched_csv']
    ]
    
    unmatched_manual_display = [
        {'manual_id': mid, 'manual_entry': manual_map.get(mid, {})}
        for mid in data['unmatched_manual']
    ]
    
    return templates.TemplateResponse(
        "reconciliation_review.html",
        {
            "request": request,
            "session_id": session_id,
            "account_id": data.get('account_id'),
            "auto_matched": auto_matched_display,
            "review_matches": review_matches_display,
            "unmatched_csv": unmatched_csv_display,
            "unmatched_manual": unmatched_manual_display,
        }
    )


@router.post("/reconciliation/finalize", response_class=HTMLResponse)
def finalize_reconciliation_post(
    session_id: str = Form(...),
    account_id: str = Form(...),
    approved_matches: Optional[str] = Form(None),
):
    """
    Process user approvals and finalize reconciliation.
    
    Applies approved matches, inserts unmatched CSV rows, updates reconciliation status.
    """
    logger.info(f"DEBUG: finalize_reconciliation_post called")
    logger.info(f"DEBUG: session_id={session_id}")
    logger.info(f"DEBUG: account_id={account_id}")
    logger.info(f"DEBUG: approved_matches={approved_matches}")
    
    if session_id not in _reconciliation_sessions:
        logger.error(f"DEBUG: Session {session_id} not found in _reconciliation_sessions")
        logger.error(f"DEBUG: Available sessions: {list(_reconciliation_sessions.keys())}")
        return HTMLResponse(
            content="<h1>Session not found</h1>",
            status_code=404
        )
    
    reconciliation_data = _reconciliation_sessions[session_id]
    logger.info(f"DEBUG: reconciliation_data keys: {reconciliation_data.keys()}")
    
    # Parse approved matches from form
    approved_indices = []
    if approved_matches:
        try:
            approved_list = json.loads(approved_matches)
            approved_indices = [(int(csv_idx), int(manual_id)) for csv_idx, manual_id in approved_list]
            logger.info(f"DEBUG: Parsed {len(approved_indices)} approved matches")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"DEBUG: Failed to parse approved_matches: {e}")
            pass
    
    try:
        # Convert account_id to int
        account_id_int = int(account_id)
        
        logger.info(f"DEBUG: Calling apply_reconciliation with account_id={account_id_int}")
        
        # Apply reconciliation
        result = apply_reconciliation(
            account_id=account_id_int,
            reconciliation_data=reconciliation_data,
            user_approvals={'approved_indices': approved_indices}
        )
        
        logger.info(f"DEBUG: apply_reconciliation returned: {result}")
        
        # Clean up session
        del _reconciliation_sessions[session_id]
        
        if result['status'] == 'success':
            categorization = result.get('categorization', {})
            categorization_html = ""
            if categorization.get('merchants_processed', 0) > 0:
                categorization_html = f"""
                <p><strong>Categorization:</strong></p>
                <ul>
                    <li>Merchants processed: {categorization.get('merchants_processed', 0)}</li>
                    <li>Transactions categorized: {categorization.get('transactions_updated', 0)}</li>
                    <li>Cache hits: {categorization.get('cache_hits', 0)}</li>
                    <li>AI calls: {categorization.get('ai_calls', 0)}</li>
                </ul>
                """
            
            return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Reconciliation Complete</title>
    <style>
        :root {{
            --bg-main: #2F2F2F;
            --bg-card: #3A3A3A;
            --border-default: #505050;
            --text-primary: #F2F2F2;
            --color-income: #3FB950;
        }}
        body {{
            font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            padding: 32px;
            background: var(--bg-main);
            color: var(--text-primary);
        }}
        .success {{
            background: rgba(63, 185, 80, 0.1);
            border: 1px solid var(--color-income);
            color: var(--color-income);
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 16px;
        }}
        ul {{
            margin: 8px 0;
            padding-left: 20px;
        }}
        li {{
            margin: 4px 0;
        }}
        a {{
            color: #58A6FF;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <h1>Reconciliation Complete</h1>
    <div class="success">
        <strong>✓ Reconciliation successful</strong>
        <p>Matched: {result['matched_count']} transactions</p>
        <p>Inserted: {result['inserted_count']} new transactions</p>
        {categorization_html}
    </div>
    <p><a href="/dashboard">→ Go to Dashboard</a></p>
</body>
</html>
            """)
        else:
            return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Reconciliation Error</title>
</head>
<body>
    <h1>Reconciliation Error</h1>
    <p>Error: {result.get('error', 'Unknown error')}</p>
    <a href="/dashboard">← Back to Dashboard</a>
</body>
</html>
            """, status_code=500)
    
    except Exception as e:
        logger.exception(f"DEBUG: Exception in finalize_reconciliation_post: {e}")
        return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Reconciliation Error</title>
</head>
<body>
    <h1>Reconciliation Error</h1>
    <p>Exception: {str(e)}</p>
    <a href="/dashboard">← Back to Dashboard</a>
</body>
</html>
        """, status_code=500)


def store_reconciliation_session(session_id: str, data: dict):
    """Store reconciliation session data for later retrieval."""
    _reconciliation_sessions[session_id] = data