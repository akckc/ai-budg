from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from services.recurring_service import (
    add_recurring_event,
    get_recurring_events,
    toggle_recurring_event_active,
)

router = APIRouter()


class RecurringAddRequest(BaseModel):
    account_id: int
    name: str
    amount: float
    category: str | None = None
    frequency: str
    day_of_month: int | None = None
    anchor_date: str
    active: bool = True


class RecurringToggleRequest(BaseModel):
    active: bool


@router.get("/recurring", response_class=HTMLResponse)
def recurring_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Recurring Events</title>
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

            h2 {
                font-size: 28px;
                margin: 0 0 32px 0;
                color: var(--text-primary);
            }

            h3 {
                font-size: 16px;
                margin: 0 0 16px 0;
                color: var(--text-primary);
                font-weight: 600;
            }

            p, label {
                color: var(--text-secondary);
                font-size: 12px;
            }

            .card {
                background: var(--bg-card);
                border: 1px solid var(--border-default);
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 24px;
            }

            .form-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(240px, 1fr));
                gap: 12px;
            }

            .field {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }

            input, select {
                padding: 8px;
                background: var(--bg-main);
                border: 1px solid var(--border-default);
                color: var(--text-primary);
                border-radius: 6px;
                font-size: 14px;
            }

            input:focus, select:focus {
                outline: none;
                border-color: var(--color-budget);
            }

            .checkbox-row {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 4px;
            }

            .checkbox-row label {
                font-size: 14px;
                color: var(--text-primary);
            }

            .checkbox-row input {
                width: auto;
                margin: 0;
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
            }

            button:hover {
                background: #6CB6FF;
            }

            .secondary-btn {
                background: var(--bg-card);
                border: 1px solid var(--border-default);
                color: var(--text-primary);
            }

            .secondary-btn:hover {
                background: var(--bg-card-hover);
            }

            .status {
                margin-top: 10px;
                min-height: 20px;
                font-size: 14px;
            }

            .status.success {
                color: var(--color-income);
            }

            .status.error {
                color: var(--color-expense);
            }

            table {
                border-collapse: collapse;
                width: 100%;
                background: var(--bg-card);
                margin-top: 16px;
            }

            th {
                color: var(--text-secondary);
                font-weight: 600;
                padding: 12px 10px;
                text-align: left;
                border-bottom: 1px solid var(--border-default);
                font-size: 14px;
            }

            td {
                border-bottom: 1px solid var(--border-default);
                padding: 10px;
                color: var(--text-primary);
                font-size: 14px;
                vertical-align: middle;
            }

            tbody tr:hover {
                background: var(--bg-card-hover);
            }

            a {
                color: var(--color-budget);
                text-decoration: none;
            }

            a:hover {
                text-decoration: underline;
            }

            .muted {
                color: var(--text-muted);
                margin-top: 8px;
                margin-bottom: 0;
            }

            @media (max-width: 900px) {
                .form-grid {
                    grid-template-columns: 1fr;
                }

                body {
                    padding: 16px;
                }
            }
        </style>
    </head>
    <body>
        <h2>Recurring Events</h2>
        <a href="/dashboard">Back to Dashboard</a>

        <div class="card">
            <h3>Add Recurring Event</h3>
            <p class="muted">Biweekly anchor date: choose any real occurrence date; we repeat every 14 days from it.</p>

            <div class="form-grid">
                <div class="field">
                    <label for="account_id">Account ID</label>
                    <input id="account_id" type="number" value="1" min="1" required>
                </div>
                <div class="field">
                    <label for="name">Name</label>
                    <input id="name" type="text" placeholder="Paycheck" required>
                </div>
                <div class="field">
                    <label for="amount">Amount</label>
                    <input id="amount" type="number" step="0.01" placeholder="2500.00" required>
                </div>
                <div class="field">
                    <label for="category">Category (optional)</label>
                    <input id="category" type="text" placeholder="Income">
                </div>
                <div class="field">
                    <label for="frequency">Frequency</label>
                    <select id="frequency">
                        <option value="monthly">monthly</option>
                        <option value="biweekly">biweekly</option>
                    </select>
                </div>
                <div class="field">
                    <label for="day_of_month">Day of Month (monthly only)</label>
                    <input id="day_of_month" type="number" min="1" max="31" placeholder="1-31">
                </div>
                <div class="field">
                    <label for="anchor_date">Anchor Date</label>
                    <input id="anchor_date" type="date" required>
                </div>
                <div class="field">
                    <label>Active</label>
                    <div class="checkbox-row">
                        <input id="active" type="checkbox" checked>
                        <label for="active">Enabled</label>
                    </div>
                </div>
            </div>

            <div style="margin-top: 12px;">
                <button id="addBtn" onclick="addRecurringEvent()">Add Recurring Event</button>
            </div>
            <div id="status" class="status"></div>
        </div>

        <div class="card">
            <h3>Existing Recurring Events</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Account</th>
                        <th>Name</th>
                        <th>Amount</th>
                        <th>Category</th>
                        <th>Frequency</th>
                        <th>Day</th>
                        <th>Anchor Date</th>
                        <th>Active</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="eventsTable"></tbody>
            </table>
        </div>

        <script>
            function formatAmount(value) {
                const amount = Number(value || 0);
                const color = amount >= 0 ? 'var(--color-income)' : 'var(--color-expense)';
                return `<span style="color: ${color};">${amount.toFixed(2)}</span>`;
            }

            async function loadRecurringEvents() {
                const res = await fetch('/recurring/list');
                const data = await res.json();

                const tbody = document.getElementById('eventsTable');
                tbody.innerHTML = '';

                data.events.forEach(event => {
                    const toggleTarget = !event.active;
                    const btnText = event.active ? 'Set Inactive' : 'Set Active';
                    const row = `
                        <tr>
                            <td>${event.id}</td>
                            <td>${event.account_name || event.account_id}</td>
                            <td>${event.name}</td>
                            <td>${formatAmount(event.amount)}</td>
                            <td>${event.category || ''}</td>
                            <td>${event.frequency}</td>
                            <td>${event.day_of_month ?? ''}</td>
                            <td>${event.anchor_date || ''}</td>
                            <td>${event.active ? 'Yes' : 'No'}</td>
                            <td>
                                <button class="secondary-btn" onclick="toggleRecurringEvent(${event.id}, ${toggleTarget})">${btnText}</button>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
            }

            async function addRecurringEvent() {
                const payload = {
                    account_id: Number(document.getElementById('account_id').value),
                    name: document.getElementById('name').value,
                    amount: Number(document.getElementById('amount').value),
                    category: document.getElementById('category').value || null,
                    frequency: document.getElementById('frequency').value,
                    day_of_month: document.getElementById('day_of_month').value
                        ? Number(document.getElementById('day_of_month').value)
                        : null,
                    anchor_date: document.getElementById('anchor_date').value,
                    active: document.getElementById('active').checked,
                };

                const status = document.getElementById('status');
                status.className = 'status';

                try {
                    const res = await fetch('/recurring/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });
                    const data = await res.json();

                    if (!res.ok) {
                        throw new Error(data.detail || 'Failed to add recurring event');
                    }

                    status.textContent = `Created recurring event #${data.id}`;
                    status.classList.add('success');

                    document.getElementById('name').value = '';
                    document.getElementById('amount').value = '';
                    document.getElementById('category').value = '';
                    document.getElementById('day_of_month').value = '';
                    document.getElementById('anchor_date').value = '';
                    document.getElementById('active').checked = true;

                    await loadRecurringEvents();
                } catch (err) {
                    status.textContent = err.message;
                    status.classList.add('error');
                }
            }

            async function toggleRecurringEvent(eventId, active) {
                try {
                    const res = await fetch(`/recurring/${eventId}/toggle`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ active }),
                    });
                    if (!res.ok) {
                        const data = await res.json();
                        throw new Error(data.detail || 'Toggle failed');
                    }
                    await loadRecurringEvents();
                } catch (err) {
                    const status = document.getElementById('status');
                    status.textContent = err.message;
                    status.className = 'status error';
                }
            }

            loadRecurringEvents();
        </script>
    </body>
    </html>
    """


@router.get("/recurring/list")
def recurring_list():
    return get_recurring_events(include_inactive=True)


@router.post("/recurring/add")
def recurring_add(payload: RecurringAddRequest):
    try:
        new_id = add_recurring_event(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"success": True, "id": new_id}


@router.post("/recurring/{event_id}/toggle")
def recurring_toggle(event_id: int, payload: RecurringToggleRequest):
    toggle_recurring_event_active(event_id=event_id, active=payload.active)
    return {"success": True}
