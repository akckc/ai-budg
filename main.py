from fastapi import FastAPI
from db import init_db
from routes.dashboard import router as dashboard_router
from routes.transactions import router as transactions_router
from routes.rules import router as rules_router
from routes.forecast import router as forecast_router
from routes.ingestion import router as ingestion_router
from routes.budgets import router as budgets_router
from routes.recurring import router as recurring_router
from routes.upload import router as upload_router
from routes.ai import router as ai_router
from routes.reconciliation import router as reconciliation_router

app = FastAPI()

init_db()

app.include_router(dashboard_router)
app.include_router(transactions_router)
app.include_router(rules_router)
app.include_router(forecast_router)
app.include_router(ingestion_router)
app.include_router(budgets_router)
app.include_router(recurring_router)
app.include_router(upload_router)
app.include_router(ai_router)
app.include_router(reconciliation_router)


@app.on_event("startup")
async def startup_event():
    import threading
    from services.telegram_bot_service import start_bot
    t = threading.Thread(target=start_bot, daemon=True)
    t.start()
    print("Telegram bot thread launched.", flush=True)

