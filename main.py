from fastapi import FastAPI
from db import init_db
from routes.dashboard import router as dashboard_router
from routes.transactions import router as transactions_router
from routes.rules import router as rules_router
from routes.forecast import router as forecast_router

app = FastAPI()

init_db()

app.include_router(dashboard_router)
app.include_router(transactions_router)
app.include_router(rules_router)
app.include_router(forecast_router)

