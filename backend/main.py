"""
main.py

BudgetNest backend entrypoint.

Stage 1 (backend foundation) provided:
- App creation + configuration
- CORS setup
- MongoDB startup/shutdown lifecycle
- Global exception handling
- The /api/health endpoint

Stage 2 adds:
- Authentication & user management routes (routes/auth.py)
- User collection index setup on startup

Stage 3 adds:
- The core personal financial engine: starting balance, transactions,
  and financial summaries (routes/finance.py, routes/transactions.py)
- Financial collection index setup on startup

Stage 4 adds, built on top of the Step 3 engine:
- Personal budgets — overall + per-category monthly limits, with
  usage computed live from the existing financial summary logic
  (routes/budgets.py)
- Payment/Bill scheduling — recurring and one-off scheduled payments,
  where marking a bill paid creates a real transaction through the
  same Step 3 create_transaction function (routes/bills.py)
- Budget/bill collection index setup on startup

Stage 5 (this stage) adds, also built on top of the Step 3 engine:
- Money Given & Money Returned — person-wise lending/return tracking
  (who money was given to, partial/multiple returns, outstanding
  amount, status), where creating a record or recording a return each
  create exactly one real transaction through the same Step 3
  create_transaction function (routes/money_given.py)
- money_given/money_returns collection index setup on startup

Stage 6 (this stage) adds, also built on top of the existing engines:
- Reminders & Upcoming Payments — extends the Step 4 "bills" model
  (rather than creating a second, competing schedule model) with
  reminder configuration, priority, and a computed UPCOMING/DUE/
  OVERDUE/PAID/CANCELLED status derived from due_date, plus overdue/
  summary/monthly-upcoming-total endpoints (routes/bills.py)
- A reporting/analytics backend foundation — monthly financial
  summary, category breakdown, income vs. expense, budget vs.
  actual, payment summary, money-given summary, and a monthly trend,
  all composed from the existing Step 3/4/5/6 engines rather than a
  second financial calculation layer (routes/reports.py)

Advanced features (push notifications, charts, receipt upload, the
React financial dashboard) are NOT included yet — those are later
stages.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import connect_to_mongo, close_mongo_connection, get_database
from routes import bills, budgets, health, auth, finance, money_given, reports, transactions
from services.user_service import ensure_indexes
from services.financial_service import ensure_indexes as ensure_financial_indexes
from services.budget_service import ensure_indexes as ensure_budget_indexes
from services.bill_service import ensure_indexes as ensure_bill_indexes
from services.money_given_service import ensure_indexes as ensure_money_given_indexes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("budgetnest.main")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="BudgetNest personal budget and expense management API.",
)

# --- CORS ---
# Origins are read from the CORS_ORIGINS environment variable (comma-separated).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Startup / shutdown lifecycle ---
@app.on_event("startup")
async def on_startup():
    logger.info("Starting %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    if not settings.SMTP_CONFIGURED:
        missing = [
            name
            for name, value in (
                ("SMTP_HOST", settings.SMTP_HOST),
                ("SMTP_USERNAME", settings.SMTP_USERNAME),
                ("SMTP_PASSWORD", settings.SMTP_PASSWORD),
            )
            if not value
        ]
        logger.warning(
            "SMTP is not fully configured (missing: %s). "
            "POST /api/auth/send-login-code will fail with 503 until "
            "these are set in backend/.env. See backend/.env.example.",
            ", ".join(missing),
        )
    await connect_to_mongo()
    # Ensure the users collection has its required indexes (e.g. unique
    # email) before the app starts accepting traffic.
    await ensure_indexes(get_database())
    await get_database().login_verification_codes.create_index("email")
    await get_database().login_verification_codes.create_index("expires_at", expireAfterSeconds=0)
    # Ensure the transactions/starting_balances collections have their
    # required indexes (user_id, transaction_date, transaction_type,
    # category, status) before the app starts accepting traffic.
    await ensure_financial_indexes(get_database())
    # Ensure the budgets/bills collections have their required indexes
    # before the app starts accepting traffic.
    await ensure_budget_indexes(get_database())
    await ensure_bill_indexes(get_database())
    # Ensure the money_given/money_returns collections have their
    # required indexes before the app starts accepting traffic.
    await ensure_money_given_indexes(get_database())


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down %s...", settings.APP_NAME)
    await close_mongo_connection()


# --- Global error handling ---
# Catches any exception not already handled by FastAPI/route-level logic
# and returns a clean, consistent JSON error response instead of leaking
# stack traces to the client.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error while processing %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# --- Routers ---
# All routes are namespaced under /api. Future stages will add their
# routers here in the same way.
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(finance.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(budgets.router, prefix="/api")
app.include_router(bills.router, prefix="/api")
app.include_router(money_given.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/")
async def root():
    """Basic root endpoint, mainly useful for a quick sanity check."""
    return {"message": "BudgetNest API — see /api/health for status."}
