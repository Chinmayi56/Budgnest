# BudgetNest

BudgetNest is a full-stack personal budget and expense management
application: budgets, expenses, income, payments, money given/returned,
and reminders — all scoped to each individual user's own data.
This repository is being built in **stages**. This README documents
everything completed so far.

## Stages Completed

- **Step 1 — Backend Foundation**: FastAPI + MongoDB skeleton, config,
  CORS, global error handling, `/api/health`.
- **Step 2 — Authentication & User Management**: registration, login,
  JWT auth, `/api/auth/me`, role-based access foundation, automated
  tests.
- **Step 3 — Core Personal Financial Engine**: starting
  balance, a unified personal transaction system (income, expenses,
  payments, money given/returned, refunds, adjustments), backend-only
  balance calculation, daily/monthly summaries, filtering, and strict
  per-user data isolation.
- **Step 4 — Personal Budget & Expense Management**: overall +
  per-category monthly budgets with live usage/remaining/status
  tracking, and recurring + one-off scheduled payments ("bills") that
  create real transactions through the Step 3 engine when paid — all
  built on top of Step 3 without duplicating its transaction/balance
  logic.
- **Step 5 — Money Given & Money Returned**:
  person-wise money-lending tracking — who money was given to, how
  much, partial/multiple returns over time, outstanding amount, and
  automatic `OUTSTANDING` → `PARTIALLY_RETURNED` → `SETTLED` status —
  where creating a record or recording a return each create exactly
  one real `MONEY_GIVEN`/`MONEY_RETURNED` transaction through the
  Step 3 engine, so the actual balance is never computed twice.
- **Step 6 — Reminders & Upcoming Payments + Reporting/Analytics
  Foundation** *(this stage)*: extends the Step 4 "bills" model
  (rather than a second, competing model) with reminder configuration
  (`reminder_enabled`/`reminder_date`), `priority`, a `description`,
  and a computed `due_status` (`UPCOMING`/`DUE`/`OVERDUE`/`PAID`/
  `CANCELLED`) derived from `due_date` — plus overdue listing, a
  payment summary, and a monthly upcoming-payments total. Also adds a
  reporting/analytics backend foundation (`/api/reports/*`) that
  composes the existing Step 3/4/5/6 engines into monthly summaries,
  category breakdowns, income-vs-expense, budget-vs-actual, and a
  monthly trend — real database data only, no charts/dashboard UI yet.

Not yet built: push/browser notifications, the React financial
dashboard, charts, advanced reports UI, calendar UI, receipt upload.
Those are later steps (Step 7 — React Frontend + Dashboard, Step 8 —
Reports, Charts & Analytics UI).

## Tech Stack

- Python
- FastAPI
- MongoDB
- Motor (`AsyncIOMotorClient`)
- Pydantic
- JWT (`PyJWT`)
- Password hashing (`bcrypt`)
- Uvicorn
- python-dotenv
- CORS (via `fastapi.middleware.cors`)

Only **one** MongoDB database is used throughout.

## Project Structure

```
BUDGETNEST/
│
├── backend/
│   ├── main.py               # FastAPI app, CORS, startup/shutdown, error handling, routers
│   ├── config.py             # Environment-variable-driven settings
│   ├── database.py           # Motor client setup + connection helpers
│   ├── requirements.txt
│   ├── .env.example
│   ├── pytest.ini
│   │
│   ├── models/
│   │   ├── user.py           # UserRole, UserStatus enums + Mongo document helpers
│   │   ├── transaction.py    # TransactionType/Status, AdjustmentDirection, PaymentMethod + Mongo document helpers
│   │   ├── budget.py         # BudgetType/Status enums + Mongo document helpers (Step 4)
│   │   ├── bill.py           # BillFrequency/Status/Priority, computed DueStatus + Mongo document helpers (Step 4, extended Step 6)
│   │   └── money_given.py    # MoneyGivenStatus/Category enums + Mongo document helpers (Step 5)
│   ├── schemas/
│   │   ├── user.py           # Pydantic request/response schemas (auth)
│   │   ├── finance.py        # Pydantic request/response schemas (starting balance, transactions, summaries)
│   │   ├── budget.py         # Pydantic request/response schemas (budgets, Step 4)
│   │   ├── bill.py           # Pydantic request/response schemas (bills/payments/reminders, Step 4, extended Step 6)
│   │   ├── money_given.py    # Pydantic request/response schemas (money given/returned, Step 5)
│   │   └── report.py         # Pydantic response schemas (reporting/analytics, Step 6)
│   ├── routes/
│   │   ├── health.py         # GET /api/health
│   │   ├── auth.py           # /api/auth/* endpoints
│   │   ├── finance.py        # /api/finance/* endpoints (starting balance, summaries)
│   │   ├── transactions.py   # /api/transactions* endpoints (CRUD)
│   │   ├── budgets.py        # /api/budgets* endpoints (Step 4)
│   │   ├── bills.py          # /api/bills* endpoints (Step 4, extended Step 6: reminders/overdue/summary)
│   │   ├── money_given.py    # /api/money-given* endpoints (Step 5)
│   │   └── reports.py        # /api/reports/* endpoints (Step 6)
│   ├── services/
│   │   ├── user_service.py       # DB access: create/find/authenticate users
│   │   ├── financial_service.py  # DB access + centralized balance/summary calculations
│   │   ├── budget_service.py     # DB access + budget usage (reuses financial_service, Step 4)
│   │   ├── bill_service.py       # DB access + pay-bill flow + Step 6 summary/monthly-upcoming (reuses financial_service)
│   │   ├── money_given_service.py  # DB access + given/return flow (reuses financial_service, Step 5)
│   │   └── report_service.py     # Composes Step 3/4/5/6 engines into report shapes (Step 6, no independent math)
│   ├── utils/
│   │   ├── security.py       # Password hashing (bcrypt)
│   │   ├── jwt_handler.py    # JWT create/decode
│   │   ├── deps.py           # get_current_user, require_roles (unused, kept for extensibility)
│   │   └── money.py          # Decimal <-> Mongo Decimal128 helpers (safe monetary representation)
│   └── tests/
│       ├── conftest.py       # In-memory Mongo test double + fixtures (incl. authenticated-client fixtures)
│       ├── test_auth.py      # Authentication test suite
│       ├── test_finance.py   # Financial engine test suite
│       ├── test_budgets.py   # Budget test suite (Step 4)
│       ├── test_bills.py     # Bills/payments test suite (Step 4)
│       ├── test_money_given.py  # Money given/returned test suite (Step 5)
│       ├── test_reminders_payments.py  # Reminders/priority/due_status/overdue/summary test suite (Step 6)
│       └── test_reports.py   # Reporting/analytics test suite (Step 6)
│
├── frontend/                  # (reserved for future stages)
│
├── .env.example
└── README.md
```

---

## Backend Setup

All commands below assume you are in the project root (`BudgetNest/`)
unless otherwise noted.

### 1. Create a Python virtual environment

**Windows (PowerShell / VS Code terminal):**

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt once
the environment is active.

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your own values:

**Windows:**

```powershell
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Then edit `backend/.env`:

```
MONGO_URL=mongodb://localhost:27017
DB_NAME=budgetnest
JWT_SECRET=change_this_to_a_long_random_secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

| Variable            | Purpose                                                 |
|----------------------|----------------------------------------------------------|
| `MONGO_URL`          | Full MongoDB connection string                          |
| `DB_NAME`            | Name of the single MongoDB database BudgetNest uses      |
| `JWT_SECRET`         | Secret key used to sign/verify JWT access tokens         |
| `JWT_ALGORITHM`      | JWT signing algorithm (e.g. `HS256`)                     |
| `JWT_EXPIRE_MINUTES` | How long an access token stays valid, in minutes         |
| `CORS_ORIGINS`       | Comma-separated list of allowed frontend origins         |

No new environment variables were added in Step 2 — the JWT variables
were already reserved in `.env.example` from Step 1 and are now
actually used.

### 4. MongoDB configuration

You need a running MongoDB instance reachable at `MONGO_URL`. Options:

- **Local MongoDB Community Server** — install it, then the default
  `mongodb://localhost:27017` will work out of the box.
- **MongoDB Atlas (cloud, free tier available)** — create a cluster, add
  your IP to the network access list, and copy the provided connection
  string into `MONGO_URL` (it will look like
  `mongodb+srv://user:password@cluster.mongodb.net`).

No manual database or collection creation is required. MongoDB creates
the database named in `DB_NAME`, and the `users` collection, automatically
the first time data is written. The backend also creates a **unique
index on `users.email`** on startup, so duplicate emails are rejected
even under concurrent requests.

### 5. Run the backend

From inside `backend/` with the virtual environment active:

```bash
python -m uvicorn main:app --reload --port 8000
```

By default this serves the API at `http://127.0.0.1:8000`.

### 6. Verify it's working

```
GET http://127.0.0.1:8000/api/health
```

```json
{
  "status": "ok",
  "service": "BudgetNest Backend",
  "version": "0.1.0",
  "message": "BudgetNest backend is running",
  "database_connected": true
}
```

Interactive API docs (Swagger UI): `http://127.0.0.1:8000/docs`
Raw OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

---

## Authentication Overview

Authentication is JWT-based and stateless. All endpoints are under
`/api/auth`.

### User Roles

BudgetNest is a personal application, not a multi-tenant company tool,
so there is a single application role:

| Role   | Access                                   |
|--------|-------------------------------------------|
| `USER` | Full access to their own personal data only |

The `role` field is kept on the user model for future extensibility,
but it is never accepted from client input — every self-registered
account is created as `USER` by the server. There is no
company-style role hierarchy (owner/accountant/employee) and no
role-based authorization in this application; per-user data isolation
is handled by always scoping database queries to the authenticated
user's id from the JWT (see "Per-User Data Isolation" below), not by
roles.

### Account Status

| Status      | Meaning                              |
|-------------|----------------------------------------|
| `ACTIVE`    | Can log in normally (default on registration) |
| `INACTIVE`  | Login blocked (`403`)                 |
| `SUSPENDED` | Login blocked (`403`)                 |

### Registration — `POST /api/auth/register`

```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "StrongPassword123"
}
```

- `password` minimum length: 8 characters.
- `role` is not a request field — every account is created with role
  `USER` server-side, regardless of anything sent in the request body.
- Duplicate email → `409 Conflict`.
- Response never includes the password or password hash.

Response (`201 Created`):

```json
{
  "id": "...",
  "full_name": "John Doe",
  "email": "john@example.com",
  "role": "USER",
  "status": "ACTIVE",
  "created_at": "...",
  "updated_at": "..."
}
```

### Login — `POST /api/auth/login`

```json
{
  "email": "john@example.com",
  "password": "StrongPassword123"
}
```

Response (`200 OK`):

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "full_name": "John Doe",
    "email": "john@example.com",
    "role": "USER",
    "status": "ACTIVE",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

- Wrong password and non-existent email return the **exact same**
  `401` error (`"Invalid email or password"`), so login cannot be used
  to enumerate which emails are registered.
- An `INACTIVE`/`SUSPENDED` account with correct credentials returns
  `403` (checked only after credentials are confirmed valid).

### Current User — `GET /api/auth/me`

Requires a valid JWT. Returns the authenticated user's safe profile
(never the password hash).

### JWT Usage

Send the token on every protected request:

```
Authorization: Bearer <access_token>
```

Missing header → `401`. Malformed/invalid/expired token → `401`.
Valid token but inactive/suspended account → `403`.

### Logout — `POST /api/auth/logout`

JWT access tokens are stateless and not stored server-side, so there is
nothing to revoke yet. This endpoint simply confirms the token was
valid; the **client is responsible for discarding the token** (clearing
it from storage/memory) to complete logout. If server-side revocation
is needed later, it can be added as a field on the existing `users`
document (e.g. `token_version`) — no new database required.

### Per-User Data Isolation

Every future financial-data route (budgets, expenses, income,
payments, money given/returned, transactions, reminders, reports)
must:

1. Depend on `get_current_user` (`utils/deps.py`) to resolve the
   authenticated user from the validated JWT.
2. Use `current_user.id` — **never** a `user_id` supplied by the
   frontend (query param, body field, etc.) — as the scoping value in
   every MongoDB read/write for that user's data.

This is the only access-control mechanism this application needs: a
single role, with strict per-user ownership checks on every query.

`utils/deps.py` also exposes a generic `require_roles(*roles)`
dependency factory. It isn't used anywhere today (there is only one
role), but is kept as a small, optional building block in case a
future role is ever introduced. It should not be used as a substitute
for the per-user data isolation described above.

---

## Core Personal Financial Engine (Step 3)

BudgetNest is a **personal** budget and expense management application
for a single individual managing their own money — it is **not** a
company ERP. There is no employee management, payroll, salary-as-a-
feature, accountant role, or company accounting anywhere in this
codebase. If a user personally receives a salary, it's recorded as a
plain `INCOME` transaction with `category: "SALARY"` — a normal
category string, not a special type or feature.

All endpoints below are under `/api/finance` and `/api/transactions`,
require a valid JWT (`Authorization: Bearer <access_token>`), and are
always scoped to `current_user.id` from that JWT — a `user_id` is
never accepted from the client. All balance/summary math happens on
the backend and is recomputed live from current MongoDB data; nothing
is hard-coded or cached.

### Money precision

Every monetary amount is stored in MongoDB as **Decimal128** (a true
base-10 decimal BSON type), converted to/from Python's `Decimal` at
the service boundary (`utils/money.py`), and all arithmetic is done
with `Decimal`. Amounts are never represented as an ordinary MongoDB
`double` and never touch binary floating-point arithmetic, so you will
never see drift like `100.0000000001`. In JSON responses, amounts
serialize as an exact numeric string, e.g. `"59000.00"`.

### Starting balance — `/api/finance/starting-balance`

| Method | Behavior |
|--------|----------|
| `POST`  | Create the starting balance. **One per user.** Returns `409` if one already exists. |
| `GET`   | Get the current starting balance. `404` if none set yet. |
| `PATCH` | The explicit adjustment mechanism — updates the amount (and optionally notes) of an already-existing starting balance. `404` if none exists yet. |

```json
POST /api/finance/starting-balance
{ "amount": 50000, "date": "2026-08-25", "notes": "Initial personal balance" }
```

### Transaction types

```
INCOME  EXPENSE  PAYMENT  MONEY_GIVEN  MONEY_RETURNED  REFUND  ADJUSTMENT
```

No `SALARY`, `EMPLOYEE_SALARY`, `PAYROLL`, or `COMPANY_PAYMENT` type
exists or will be added to this list.

### Transaction statuses & balance rules

| Status | Effect on `current_balance` |
|--------|------------------------------|
| `COMPLETED` | Applied normally, per the sign table below. |
| `PENDING`   | Never applied to `current_balance`. If the type is `EXPENSE`, `PAYMENT`, or `MONEY_GIVEN`, it counts as an **upcoming committed amount** and is subtracted separately to produce `available_balance` (see Financial Summary below). |
| `CANCELLED` | Never applied to any calculation, but the record is kept for history (see Deletion/Reversal Policy). |

| Type             | Effect on balance (when `COMPLETED`) |
|------------------|----------------------------------------|
| `INCOME`         | increases |
| `EXPENSE`        | decreases |
| `PAYMENT`        | decreases |
| `MONEY_GIVEN`    | decreases |
| `MONEY_RETURNED` | increases |
| `REFUND`         | increases |
| `ADJUSTMENT`     | `amount` is always a positive magnitude; a required `adjustment_direction` field (`INCREASE` or `DECREASE`) says which way it moves the balance — keeps amount validation (`> 0`) consistent across every transaction type. |

### Transaction endpoints — `/api/transactions`

| Method   | Path                          | Behavior |
|----------|--------------------------------|----------|
| `POST`   | `/api/transactions`            | Create a transaction. |
| `GET`    | `/api/transactions`            | List the caller's own transactions. Paginated (`page`, `page_size`), sorted by `transaction_date` descending. Filters: `transaction_type`, `category`, `status`, `payment_method`, `person_name`, `start_date`, `end_date`. |
| `GET`    | `/api/transactions/{id}`       | Get a single transaction. `404` if it doesn't exist or belongs to another user. |
| `PATCH`  | `/api/transactions/{id}`       | Partial update. Only supplied fields change. |
| `DELETE` | `/api/transactions/{id}`       | **Cancellation, not a hard delete** — see below. |

```json
POST /api/transactions
{
  "transaction_type": "EXPENSE",
  "amount": 300,
  "category": "FOOD",
  "description": "Lunch",
  "payment_method": "UPI",
  "transaction_date": "2026-08-25",
  "status": "COMPLETED",
  "notes": "Lunch"
}
```

Categories are free-form, normalized strings (uppercased), not a
locked enum — `GET /api/finance/categories` returns a suggested,
non-exhaustive starting list (`FOOD`, `GROCERIES`, `TRAVEL`, `FUEL`,
`SHOPPING`, `ENTERTAINMENT`, `RENT`, `ELECTRICITY`, `INTERNET`,
`PHONE`, `EDUCATION`, `HEALTH`, `SUBSCRIPTIONS`, `BILLS`, `SALARY`,
`OTHER`) so the set can grow without a schema change. Payment methods
(`CASH`, `UPI`, `BANK_TRANSFER`, `CREDIT_CARD`, `DEBIT_CARD`, `OTHER`)
are a small fixed enum.

### Deletion / Reversal Policy

`DELETE /api/transactions/{id}` never hard-deletes a `COMPLETED`
transaction — it marks it `CANCELLED` instead. This removes its effect
from every balance/summary calculation while keeping the record in
history, so financial history always stays reliable and auditable.
There is no endpoint that permanently erases a transaction document.

### Financial Summary — `GET /api/finance/summary`

```json
{
  "starting_balance": "50000.00",
  "total_income": "25000.00",
  "total_expenses": "8000.00",
  "total_payments": "5000.00",
  "total_money_given": "5000.00",
  "total_money_returned": "2000.00",
  "total_refunds": "0.00",
  "total_adjustments": "0.00",
  "current_balance": "59000.00",
  "pending_commitments": "0.00",
  "available_balance": "59000.00"
}
```

`current_balance` reflects only `COMPLETED` transactions.
`pending_commitments` is the sum of `PENDING` `EXPENSE`/`PAYMENT`/
`MONEY_GIVEN` amounts (upcoming payments not yet completed).
`available_balance = current_balance - pending_commitments` — the
backend foundation for future reminder/upcoming-payment features.

### Daily Summary — `GET /api/finance/daily-summary?date=2026-08-25`

```json
{
  "date": "2026-08-25",
  "total_income": "0.00",
  "total_expenses": "450.00",
  "total_payments": "0.00",
  "total_money_given": "0.00",
  "total_money_returned": "0.00",
  "total_refunds": "0.00",
  "transaction_count": 2,
  "categories": { "FOOD": "300.00", "TRAVEL": "150.00" }
}
```

### Monthly Summary — `GET /api/finance/monthly-summary?month=8&year=2026`

Same shape as the daily summary, aggregated over the whole calendar
month, plus `month`/`year` instead of `date`.

### User Data Isolation (financial data)

Every route in `routes/finance.py` and `routes/transactions.py`
depends on `get_current_user` and passes only `current_user.id` into
`services/financial_service.py` — every MongoDB query for starting
balances and transactions is filtered by `user_id`. A transaction that
exists but belongs to a different user returns `404` (not `403`), so
its existence is never leaked to a user who doesn't own it. This is
covered explicitly by `test_user_data_isolation_transactions` and
`test_user_data_isolation_balance_and_summary` in
`tests/test_finance.py`.

### MongoDB Indexes (Step 3)

Created idempotently on startup (`services/financial_service.py:ensure_indexes`):

- `transactions.user_id`
- `transactions.transaction_date`
- `transactions.transaction_type`
- `transactions.category`
- `transactions.status`
- `starting_balances.user_id` (unique — enforces one starting balance per user)

---

## Personal Budgets & Bills (Step 4)

Built entirely on top of the Step 3 engine above — no second
transaction system, no second balance calculation, no duplicate
MongoDB collections for the same financial concept. Budgets and bills
each have their own collection (`budgets`, `bills`), but neither one
stores or recomputes a balance/spend total independently:

- **Budgets** never calculate spend themselves. Every usage number
  comes straight from `financial_service.calculate_monthly_summary()`
  — `total_expenses` for an `OVERALL` budget, or the matching entry
  in `categories` for a `CATEGORY` budget.
- **Bills** never adjust the balance themselves. Marking a bill paid
  calls `financial_service.create_transaction()` directly to create a
  real `PAYMENT` transaction — the same transactions collection and
  balance math used everywhere else.

### Budgets — `/api/budgets`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/budgets` | Create an `OVERALL` or `CATEGORY` budget for a given month/year. `409` if one already exists for that scope — use `PATCH` instead. |
| `GET` | `/api/budgets?month=8&year=2026` | List the user's budgets (optionally filtered by month/year), each with live usage. |
| `GET` | `/api/budgets/{budget_id}` | Get a single budget with live usage. |
| `PATCH` | `/api/budgets/{budget_id}` | Update `limit_amount` and/or `notes`. |
| `DELETE` | `/api/budgets/{budget_id}` | Delete a budget. Safe as a hard delete — budgets are planning config, not financial history, so this never touches the underlying transactions. |

Example create request:

```json
{
  "budget_type": "CATEGORY",
  "category": "FOOD",
  "limit_amount": 5000,
  "month": 8,
  "year": 2026
}
```

Example response (`GET`/`POST`) — usage fields are always computed
live, never stored:

```json
{
  "id": "66d1f0...",
  "budget_type": "CATEGORY",
  "category": "FOOD",
  "limit_amount": "5000.00",
  "month": 8,
  "year": 2026,
  "spent_amount": "3200.00",
  "remaining_amount": "1800.00",
  "percentage_used": 64.0,
  "budget_status": "ON_TRACK"
}
```

`budget_status` is computed (never stored) from `spent / limit`:

- `ON_TRACK` — below 80% of the limit
- `WARNING` — 80%–100% of the limit
- `EXCEEDED` — over 100% of the limit

Only `COMPLETED` expenses count toward `spent_amount` — `PENDING` and
`CANCELLED` transactions are excluded, exactly as in the Step 3
monthly summary.

### Bills / Payments — `/api/bills`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/bills` | Create a recurring (`is_recurring: true` + `frequency`) or one-off (`is_recurring: false`) scheduled payment. |
| `GET` | `/api/bills` | List bills, with optional `status`, `is_recurring`, `category`, `due_before`, `due_after` filters. |
| `GET` | `/api/bills/upcoming?days=30` | `ACTIVE` bills due within the next N days, soonest first. |
| `GET` | `/api/bills/{bill_id}` | Get a single bill. |
| `PATCH` | `/api/bills/{bill_id}` | Update any bill field (amount, due date, frequency, status, ...). |
| `DELETE` | `/api/bills/{bill_id}` | Cancel a bill (soft delete — sets `status: CANCELLED`, never hard-deletes it). |
| `POST` | `/api/bills/{bill_id}/pay` | Mark the bill paid: creates a real `COMPLETED` `PAYMENT` transaction, then advances `due_date` (recurring) or sets `status: COMPLETED` (one-off). `409` if the bill isn't `ACTIVE`. |

Recurring frequencies: `WEEKLY`, `BIWEEKLY`, `MONTHLY`, `YEARLY`.

Example create request (recurring):

```json
{
  "name": "Rent",
  "amount": 15000,
  "due_date": "2026-09-01",
  "is_recurring": true,
  "frequency": "MONTHLY",
  "category": "RENT"
}
```

Example `POST /api/bills/{bill_id}/pay` response — `due_date` has
already advanced one month, `status` stays `ACTIVE`:

```json
{
  "id": "66d1f0...",
  "name": "Rent",
  "amount": "15000.00",
  "status": "ACTIVE",
  "due_date": "2026-10-01",
  "last_paid_date": "2026-09-01",
  "last_transaction_id": "66d1f9..."
}
```

For a one-off bill, paying it instead sets `status: "COMPLETED"` and
leaves `due_date` unchanged. Either way, `GET /api/finance/summary`
immediately reflects the new `PAYMENT` transaction — there is no
separate bill-balance to keep in sync.

### User Data Isolation (Step 4)

Every route in `routes/budgets.py` and `routes/bills.py` depends on
`get_current_user` and passes only `current_user.id` into
`services/budget_service.py` / `services/bill_service.py`, exactly
like Step 3 — a budget or bill that exists but belongs to a different
user returns `404`, never leaking its existence. Covered by
`test_budget_user_data_isolation` and `test_bill_user_data_isolation`.

### MongoDB Indexes (Step 4)

Created idempotently on startup:

- `budgets.user_id`
- `budgets.(user_id, month, year)`
- `budgets.(user_id, month, year, budget_type, category)` (unique — enforces one budget per scope per month)
- `bills.user_id`
- `bills.due_date`
- `bills.status`
- `bills.(user_id, status, due_date)`

---

## Money Given & Money Returned (Step 5)

Built entirely on top of the Step 3 engine, the same way Step 4 was —
no second balance calculation, no duplicate financial-totals logic.
Two new collections (`money_given`, `money_returns`) track the
*lending relationship* — who, how much, how much has come back, and
what's still outstanding — but neither one stores or recomputes a
balance independently:

- Creating a money-given record calls
  `financial_service.create_transaction()` once to create a real
  `COMPLETED` `MONEY_GIVEN` transaction, and stores that transaction's
  id as `given_transaction_id`.
- Recording a return calls `financial_service.create_transaction()`
  once to create a real `COMPLETED` `MONEY_RETURNED` transaction, and
  stores that transaction's id on the return document as
  `return_transaction_id`.

Each money-given/return document always corresponds to **exactly
one** Step 3 transaction — never zero, never two — which is what
prevents double-counting (see `models/money_given.py`).

### Money Given / Returned — `/api/money-given`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/money-given` | Record money given to a person. Creates a real `COMPLETED` `MONEY_GIVEN` transaction. Initial `amount_returned` is `0`, `outstanding_amount` equals the full amount, `status` is `OUTSTANDING`. |
| `GET` | `/api/money-given` | List the user's records, paginated, sorted by `given_date` desc. Filters: `person_name`, `status`, `category`, `payment_method`, `start_date`, `end_date`. |
| `GET` | `/api/money-given/summary` | Overall totals: `total_money_given`, `total_money_returned`, `total_outstanding`, `active_records`, `settled_records`. `CANCELLED` records are excluded. |
| `GET` | `/api/money-given/person-summary` | Totals aggregated per `person_name`: `total_given`, `total_returned`, `outstanding`. |
| `GET` | `/api/money-given/{id}` | Get a single record, including its full `returns` history. |
| `PATCH` | `/api/money-given/{id}` | Update metadata only: `person_name`, `reason`, `category`, `expected_return_date`, `notes`. Amounts and status can never be changed here. |
| `DELETE` | `/api/money-given/{id}` | Cancel (safe reversal, never a hard delete) — see below. `409` if already `CANCELLED`. |
| `POST` | `/api/money-given/{id}/return` | Record a full or partial return. Creates a real `COMPLETED` `MONEY_RETURNED` transaction, updates `amount_returned`/`outstanding_amount`, and recalculates `status`. Call again for further partial returns. `422` if the amount exceeds the current outstanding amount; `409` if the record is already `SETTLED`/`CANCELLED`. |
| `GET` | `/api/money-given/{id}/returns` | Full return history for one record, oldest first. |

Example create request:

```json
{
  "person_name": "Rahul",
  "amount": 5000,
  "reason": "Personal loan",
  "category": "LOAN",
  "payment_method": "UPI",
  "given_date": "2026-09-01",
  "expected_return_date": "2026-09-15",
  "notes": "Temporary personal loan"
}
```

Example response after two partial returns (`2000` then `3000`):

```json
{
  "id": "66d1f0...",
  "person_name": "Rahul",
  "amount_given": "5000.00",
  "amount_returned": "5000.00",
  "outstanding_amount": "0.00",
  "status": "SETTLED",
  "given_date": "2026-09-01",
  "given_transaction_id": "66d1f1...",
  "returns": [
    {"amount": "2000.00", "return_date": "2026-09-05", "payment_method": "UPI", "return_transaction_id": "66d1f2..."},
    {"amount": "3000.00", "return_date": "2026-09-10", "payment_method": "BANK_TRANSFER", "return_transaction_id": "66d1f3..."}
  ]
}
```

Status is always derived automatically from the amounts, never set
directly by the client:

- `OUTSTANDING` — `amount_returned` is `0`.
- `PARTIALLY_RETURNED` — `0 < amount_returned < amount_given`.
- `SETTLED` — `amount_returned >= amount_given` (`outstanding_amount` is `0`).
- `CANCELLED` — only set explicitly, via `DELETE`.

Categories: `LOAN`, `FAMILY`, `FRIEND`, `EMERGENCY`, `PERSONAL`,
`OTHER` (personal categories only — see "Intentionally Not Included"
below). Payment methods reuse the Step 3 set: `CASH`, `UPI`,
`BANK_TRANSFER`, `CREDIT_CARD`, `DEBIT_CARD`, `OTHER`.

### Deletion / Cancellation Policy (Step 5)

Money given and money returned are financial history, so `DELETE
/api/money-given/{id}` never hard-deletes anything. It:

1. Marks the linked `MONEY_GIVEN` transaction `CANCELLED` (removing
   its effect from `current_balance`).
2. Marks every linked `MONEY_RETURNED` transaction `CANCELLED` too, so
   a partially-returned record is fully reversed, not left half-applied.
3. Sets the money-given record's own `status` to `CANCELLED`.
4. Leaves every `money_returns` document in place, untouched — the
   full return history stays visible via `GET .../returns`, it simply
   no longer counts toward any balance or summary total.

### Step 3 Balance Integration & No Double-Counting (Step 5)

`MONEY_GIVEN` continues to decrease `current_balance` and
`MONEY_RETURNED` continues to increase it, exactly as defined in Step
3 (`models/transaction.py` `DECREASING_TYPES`/`INCREASING_TYPES`) —
Step 5 adds no second balance calculation anywhere. Given a starting
balance of `50000`:

```text
Money Given ₹5,000   → current_balance = 45000.00
Return ₹2,000        → current_balance = 47000.00
Return ₹3,000         → current_balance = 50000.00
```

Because each money-given/return document stores the id of the single
Step 3 transaction it created (`given_transaction_id` /
`return_transaction_id`), and that transaction is only ever created
once (at record-creation / return-recording time), the same financial
event can never be counted twice — covered by
`test_no_double_counting_of_given_and_returned`.

### User Data Isolation (Step 5)

Every route in `routes/money_given.py` depends on `get_current_user`
and passes only `current_user.id` into
`services/money_given_service.py`, exactly like Steps 3–4 — a record
that exists but belongs to a different user returns `404` from every
endpoint (view, return history, add a return, update, cancel), and is
excluded from that other user's list/summary/person-summary. Two
different users can each track a person with the same name (e.g. both
have a "Rahul") without any collision, since every query is scoped by
`user_id`. Covered by `test_money_given_user_data_isolation` and
`test_same_person_name_isolated_across_users`.

### MongoDB Indexes (Step 5)

Created idempotently on startup:

- `money_given.user_id`
- `money_given.status`
- `money_given.person_name`
- `money_given.given_date`
- `money_given.(user_id, status, given_date)`
- `money_returns.money_given_id`
- `money_returns.user_id`

---

## Reminders & Upcoming Payments (Step 6)

Step 6 does **not** introduce a second scheduled-payment model. It
extends the existing Step 4 `bills` collection/model
(`models/bill.py`, `services/bill_service.py`) in place, so recurring
vs. one-off scheduling, `next_due_date()`, and the pay-a-bill →
create-a-real-`PAYMENT`-transaction flow all stay exactly as Step 4
built them. What's new:

- **`description`** — free-text detail, separate from `name`.
- **`priority`** — `LOW` / `MEDIUM` / `HIGH` (defaults to `MEDIUM`).
- **`reminder_enabled` / `reminder_date`** — reminder *data* only.
  There is no browser/mobile push notification system yet (spec
  section 12) — that belongs to the future React notification UI.
  `reminder_date` must be on or before `due_date`.
- **`due_status`** (computed, never stored) — `UPCOMING` / `DUE` /
  `OVERDUE` / `PAID` / `CANCELLED`, derived every time from the
  existing lifecycle `status` (`ACTIVE`/`PAUSED`/`CANCELLED`/
  `COMPLETED`) plus `due_date` vs. today (`models/bill.py
  compute_due_status()`). Keeping this derived rather than a second
  stored status field means the two can never drift out of sync.

### New/updated endpoints — `/api/bills`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/bills/upcoming?days=30&category=` | *(Step 4, extended)* Now also accepts a `category` filter. |
| `GET` | `/api/bills/overdue` | `ACTIVE` bills whose `due_date` has already passed (`due_status: OVERDUE`). |
| `GET` | `/api/bills/summary` | `{upcoming_count, due_count, overdue_count, paid_count, upcoming_amount, due_amount, overdue_amount}` — all computed live from current bills + `PAYMENT` transactions, never hard-coded. |
| `GET` | `/api/bills/monthly-upcoming?month=&year=` | Total of `ACTIVE` bills due within the given month (defaults to the current month) — explicitly a **future committed amount**, never actual spending. |
| `POST` / `PATCH` | `/api/bills`, `/api/bills/{id}` | *(Step 4, extended)* Now also accept `description`, `priority`, `reminder_enabled`, `reminder_date`. |

Example create request:

```json
{
  "name": "Internet Bill",
  "amount": 799,
  "category": "BILLS",
  "payment_method": "UPI",
  "due_date": "2026-09-10",
  "recurrence": "MONTHLY",
  "reminder_enabled": true,
  "reminder_date": "2026-09-08",
  "notes": "Home internet"
}
```

> Note: the request/response field is named `frequency` (matching the
> existing Step 4 schema — `WEEKLY`/`BIWEEKLY`/`MONTHLY`/`YEARLY`),
> not `recurrence`; `is_recurring: true` is required alongside it.

### Recurring payment behavior

Unchanged from Step 4, now surfaced through `due_status` too: paying
September's rent (`POST /api/bills/{id}/pay`) creates one `COMPLETED`
`PAYMENT` transaction, advances `due_date` to October, and the bill's
`due_status` immediately reads back as `UPCOMING` again — no duplicate
bill document is ever created for the next occurrence; the same
document's `due_date` simply moves forward
(`models/bill.py next_due_date()`).

### Mark-as-paid & no double-counting

Exactly as Step 4 built it: `POST /api/bills/{id}/pay`

1. Creates one `COMPLETED` `PAYMENT` transaction via
   `financial_service.create_transaction()` — the single source of
   truth for balance-affecting data — which immediately reduces
   `current_balance`/increases `total_payments` in
   `/api/finance/summary`.
2. Sets `due_status` to `PAID` (one-off, via lifecycle `status:
   COMPLETED`) or advances `due_date` and keeps the bill `ACTIVE`
   (recurring).
3. A bill that isn't `ACTIVE` (already paid one-off, paused, or
   cancelled) returns `409` from `/pay` — so a completed one-off bill
   can never be paid, and therefore never double-deducted, twice.

### Upcoming payments vs. actual expenses (Step 3/17 integration)

Scheduled/upcoming bills **never** touch `current_balance` or
`available_balance` — they only exist in the `bills` collection until
actually paid. `GET /api/bills/monthly-upcoming` and
`GET /api/reports/monthly-summary`'s `upcoming_payments` field are
purely informational totals of *future committed* amounts, computed
separately from, and never subtracted from, the Step 3
`current_balance` (see `services/report_service.py
monthly_financial_summary()`).

### User Data Isolation (Step 6)

`routes/bills.py` and `routes/reports.py` depend on
`get_current_user` exactly like every prior step — `overdue`,
`summary`, and `monthly-upcoming` all query
`{"user_id": current_user.id, ...}` only, and every `/api/reports/*`
endpoint composes per-user service calls the same way. Covered by
`test_reminder_payment_user_data_isolation` and
`test_reports_user_data_isolation`.

---

## Reporting & Analytics Backend Foundation (Step 6)

STEP 8 will build the actual React charts/dashboard. STEP 6 only adds
the backend JSON those charts will eventually consume
(`services/report_service.py`, `routes/reports.py`) — no chart
rendering, no dashboard UI. Every number is computed by **composing**
the existing engines (Step 3 `financial_service`, Step 4
`budget_service`/`bill_service`, Step 5 `money_given_service`) —
there is no second, independent financial-calculation layer.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/reports/monthly-summary?month=&year=` | `{month, total_income, total_expenses, total_payments, money_given, money_returned, upcoming_payments, net_change}`. `net_change` is the real signed balance effect of that month's `COMPLETED` transactions (`total_income − total_expenses − money_given + money_returned`, reusing `models/transaction.py`'s `signed_effect()`); `upcoming_payments` is informational only and is **not** part of `net_change`. |
| `GET` | `/api/reports/category-summary?month=&year=` | `{month, categories: [{category, amount}]}` — the same category breakdown `financial_service.calculate_monthly_summary()` already computes. |
| `GET` | `/api/reports/income-expense-summary?month=&year=` | `{month, total_income, total_expenses, net}`. |
| `GET` | `/api/reports/budget-summary?month=&year=` | `{month, year, budgets: [...]}` — reuses `budget_service.get_budgets_with_usage()` verbatim (Step 4's budget engine, not a second one). |
| `GET` | `/api/reports/payment-summary` | Identical shape to `GET /api/bills/summary` (reuses `bill_service.get_payment_summary()`). |
| `GET` | `/api/reports/money-given-summary` | Identical shape to `GET /api/money-given/summary` (reuses `money_given_service.get_summary()`). |
| `GET` | `/api/reports/monthly-trend?months=6&end_month=&end_year=` | `{points: [{month, total_income, total_expenses}, ...]}` — the trailing N months, oldest first, each computed from real per-month data (a month with no transactions correctly reports `0.00`, never invented data). |

`month`/`year` default to the current month/year on every endpoint
above when omitted. All filtering (`month`, `year`, `months`,
`end_month`, `end_year`) is scoped to the authenticated user exactly
like every other endpoint in the project.

---

## Running Tests

Tests use an in-memory MongoDB-compatible test double
(`mongomock-motor`) so they run without needing a live MongoDB server,
while still exercising the real FastAPI routes end-to-end over HTTP.
The actual running application always uses real MongoDB through Motor
— the mock is a test-only double, wired in via `tests/conftest.py`.

From `backend/`, with the virtual environment active and dependencies
installed:

```bash
python -m pytest -v
```

Expected: **132 passed** —

- `test_auth.py` (**17**): registration (success, duplicate email,
  client-supplied role is ignored, weak password), login (success,
  wrong password, non-existent user, inactive/suspended account),
  `/auth/me` (valid/missing/malformed/invalid/expired token), logout,
  password hashing safety, and the Step 1 health endpoint.
- `test_finance.py` (**29**): starting balance (create/get/adjust,
  duplicate rejected, invalid amount), every transaction type and
  status combination, the exact balance-calculation example from the
  spec, pending-vs-completed-vs-cancelled balance effects, adjustment
  increase/decrease, listing/filtering/pagination, single-transaction
  retrieval (including invalid id → `404`), updates, daily and monthly
  summaries, full user-data-isolation coverage (transactions, starting
  balance, and summaries), unauthorized access (`401`), and invalid
  amount/type validation (`422`).
- `test_budgets.py` (**12**): overall + category budget creation,
  category required/rejected validation, duplicate-budget rejection,
  usage computed only from `COMPLETED` expenses (pending/cancelled
  excluded), per-category isolation, `WARNING`/`EXCEEDED` status
  thresholds, update, delete, auth required, and user data isolation.
- `test_bills.py` (**11**): one-off and recurring bill creation,
  frequency required/rejected validation, paying a one-off bill
  (creates a `PAYMENT` transaction, bill → `COMPLETED`, and the new
  transaction is reflected in `/api/finance/summary`), paying a
  recurring bill (advances `due_date`, stays `ACTIVE`), paying a
  non-`ACTIVE` bill rejected (`409`), cancel as soft-delete, the
  `/upcoming` window filter, auth required, and user data isolation.
- `test_money_given.py` (**37**): creation and validation (invalid/
  negative/zero amount, missing person name, invalid expected-return
  date, invalid category/payment method/date), full return, partial
  return, three-return settlement sequence, return exceeding
  outstanding rejected (`422`), return against a settled record
  rejected (`409`), return against an unknown record (`404`), full
  return-history preservation across multiple returns, listing +
  filtering by `status`/`person_name`, single-record retrieval
  (including invalid id → `404`), metadata-only updates, cancellation
  (reverses the balance, preserves history, `409` if already
  cancelled, reverses linked returns too), overall summary and
  cancelled-record exclusion, person-wise summary, total-outstanding-
  across-people, the exact Step 3 balance-integration example from
  the spec, no-double-counting verification (transaction counts +
  totals), settled-record-has-zero-outstanding, full user data
  isolation (view/returns/add-return/update/cancel/list/summary/
  person-summary), auth required, and same-person-name isolation
  across two different users.
- `test_reminders_payments.py` (**17**): create with
  reminder/priority, reminder-date-after-due-date rejected,
  reminder-enabled-without-reminder-date rejected, invalid amount/
  recurrence rejected, `due_status` = `DUE` (today) / `OVERDUE` /
  `UPCOMING` / `PAID` / `CANCELLED`, `/overdue` filtering (includes
  overdue, excludes future), mark-as-paid creates exactly one
  transaction with no double-counting on a second `/pay` attempt
  (`409`), recurring next-occurrence reads back `UPCOMING`, updating
  reminder/priority/description fields, `/summary` reflects real
  data and matches `/api/reports/payment-summary`, `/monthly-upcoming`
  total, auth required, and user data isolation across overdue/
  summary/single-record lookups.
- `test_reports.py` (**11**): monthly summary keeps
  income/expenses/money-given/money-returned/upcoming-payments
  logically separate with a verified `net_change` calculation,
  defaults to the current month, category summary, income-vs-expense,
  budget-vs-actual (reuses the Step 4 engine — verified against a
  real `WARNING`-threshold budget), the payment-summary and
  money-given-summary report endpoints (reusing Steps 5/6 engines),
  a 3-month trend with real zeros for unseeded months (oldest first),
  auth required, and user data isolation.

To run just the Step 6 suites:

```bash
python -m pytest tests/test_reminders_payments.py tests/test_reports.py -v
```

To run just the Step 5 suite:

```bash
python -m pytest tests/test_money_given.py -v
```

To run just the Step 4 suites:

```bash
python -m pytest tests/test_budgets.py tests/test_bills.py -v
```

To run just the Step 3 financial-engine suite:

```bash
python -m pytest tests/test_finance.py -v
```

---

## Running in VS Code on Windows — exact commands

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

Edit `backend\.env` and fill in real values (at minimum confirm
`MONGO_URL` points to a running MongoDB instance, and set a real
`JWT_SECRET`).

```powershell
python -m uvicorn main:app --reload --port 8000
```

Run the full test suite:

```powershell
python -m pytest -v
```

Visit `http://127.0.0.1:8000/api/health` and
`http://127.0.0.1:8000/docs` to confirm the server is running.

> If `python` isn't recognized, use `py` instead: `py -m venv venv`,
> `py -m pip install -r requirements.txt`, `py -m uvicorn main:app --reload --port 8000`,
> `py -m pytest -v`.

### Endpoints to try in Swagger (`/docs`)

1. `POST /api/auth/register` — create a user (always role `USER`)
2. `POST /api/auth/login` — log in, copy the `access_token` from the response
3. Click **Authorize** in Swagger UI, enter `Bearer <access_token>`
4. `GET /api/auth/me` — confirm it returns your user
5. `POST /api/finance/starting-balance` — `{ "amount": 50000, "date": "2026-08-25" }`
6. `POST /api/transactions` — create an `INCOME`, an `EXPENSE`, etc.
7. `GET /api/finance/summary` — confirm `current_balance` matches your transactions
8. `GET /api/finance/daily-summary?date=2026-08-25` and `GET /api/finance/monthly-summary?month=8&year=2026`
9. `GET /api/transactions` — try the `transaction_type`, `category`, `start_date`/`end_date` filters
10. `POST /api/budgets` — `{ "budget_type": "OVERALL", "limit_amount": 20000, "month": 8, "year": 2026 }`, then another with `"budget_type": "CATEGORY", "category": "FOOD"`
11. `GET /api/budgets?month=8&year=2026` — confirm `spent_amount`/`budget_status` reflect the transactions you created
12. `POST /api/bills` — `{ "name": "Rent", "amount": 15000, "due_date": "2026-09-01", "is_recurring": true, "frequency": "MONTHLY" }`
13. `POST /api/bills/{bill_id}/pay` — confirm `due_date` advances and `GET /api/finance/summary` now shows the payment
14. `GET /api/bills/upcoming?days=30`
15. `GET /api/bills/overdue`, `GET /api/bills/summary`, `GET /api/bills/monthly-upcoming?month=9&year=2026`
16. `PATCH /api/bills/{bill_id}` — `{ "reminder_enabled": true, "reminder_date": "2026-08-29", "priority": "HIGH" }`
17. `GET /api/reports/monthly-summary?month=8&year=2026` — confirm `upcoming_payments` and `net_change` are logically separate
18. `GET /api/reports/category-summary?month=8&year=2026`, `GET /api/reports/budget-summary?month=8&year=2026`, `GET /api/reports/monthly-trend?months=6`
19. `POST /api/auth/logout`
20. `GET /api/health` — confirm Step 1 still works

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'fastapi'` (or similar)**
Your virtual environment likely isn't active, or dependencies weren't
installed. Re-run `venv\Scripts\activate` (Windows) or
`source venv/bin/activate` (macOS/Linux), then
`python -m pip install -r requirements.txt`.

**`RuntimeError: Missing required environment variable: 'MONGO_URL'`**
You haven't created `backend/.env`, or a required variable is missing
from it. Copy `backend/.env.example` to `backend/.env` and fill in the
values.

**`database_connected: false` in the health-check response**
The API started, but couldn't reach MongoDB. Check that:
- MongoDB is actually running (`mongod` locally, or your Atlas cluster
  is active).
- `MONGO_URL` in `.env` is correct.
- If using Atlas, your current IP is allow-listed under Network Access.

**Server hangs on startup with no MongoDB running**
`connect_to_mongo()` verifies connectivity with a ping before the app
finishes starting up, so it will hang/retry if MongoDB is unreachable.
Start MongoDB first (or point `MONGO_URL` at a reachable instance),
then start uvicorn.

**`401 Unauthorized` on `/api/auth/me`**
Make sure you're sending `Authorization: Bearer <token>` with a token
from a recent `/api/auth/login` response, and that it hasn't expired
(`JWT_EXPIRE_MINUTES`).

**`409 Conflict` on registration**
That email is already registered — log in instead, or use a different
email.

**CORS errors from the frontend**
Add the frontend's origin (e.g. `http://localhost:3000`) to
`CORS_ORIGINS` in `.env`, comma-separated if there are multiple.

**Port already in use**
Run on a different port:
```bash
python -m uvicorn main:app --reload --port 8001
```

**Changes not reflected while the server is running**
Make sure you started uvicorn with `--reload`, and that you're editing
files inside `backend/`.

**`pytest` not found / tests fail to collect**
Make sure the virtual environment is active and
`python -m pip install -r requirements.txt` completed successfully
(it includes `pytest`, `pytest-asyncio`, `httpx`, `mongomock-motor`).

**`409 Conflict` on `POST /api/finance/starting-balance`**
A starting balance already exists for this account. Use
`PATCH /api/finance/starting-balance` to adjust it instead.

**`422 Unprocessable Entity` creating an `ADJUSTMENT` transaction**
`adjustment_direction` (`INCREASE` or `DECREASE`) is required when
`transaction_type` is `ADJUSTMENT`, and must be omitted for every
other type.

**`409 Conflict` on `POST /api/budgets`**
A budget already exists for that scope (overall, or that category)
for the given month/year. Use `PATCH /api/budgets/{budget_id}`
instead.

**`422 Unprocessable Entity` creating a budget**
`category` is required when `budget_type` is `CATEGORY`, and must be
omitted when `budget_type` is `OVERALL`.

**`422 Unprocessable Entity` creating a bill**
`frequency` is required when `is_recurring` is `true`, and must be
omitted when `is_recurring` is `false`.

**`409 Conflict` on `POST /api/bills/{bill_id}/pay`**
The bill isn't `ACTIVE` (it's `PAUSED`, `CANCELLED`, or already
`COMPLETED`). Only `ACTIVE` bills can be paid.

---

## What's Intentionally Not Included Yet

Per the staged development plan, this stage does **not** include: the
React financial dashboard, charts, advanced reports UI, a reminder/
calendar UI, browser or mobile push notifications, receipt upload, or
the visual reporting/analytics system (Step 6 only builds the backend
JSON that will power it). Those arrive in Step 7 (React Frontend +
Dashboard) and Step 8 (Reports, Charts & Analytics UI), built on top
of this financial-engine foundation, and every one of them must
continue to scope its queries to the authenticated user's own id.

BudgetNest also intentionally does **not** and **will not** include:
employee management, employee salaries/payroll, an accountant role, or
company management/accounting modules — it is a personal budget
application, not a company ERP.
