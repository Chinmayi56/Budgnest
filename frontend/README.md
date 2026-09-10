# BudgetNest — Frontend Demo

A simple, working personal finance dashboard demo. **Everything runs
in the browser** — data is stored in `localStorage`, and there is no
real backend/authentication wired up (the `backend/` folder in this
repo is not used by this demo).

## Tech Stack

- React 18 + Vite
- React Router DOM
- Tailwind CSS
- Recharts
- Lucide React icons

## Run it

```bash
cd frontend
npm install
npm run dev
```

Then open the URL Vite prints (usually `http://localhost:5173`).

To build for production:

```bash
npm run build
npm run preview
```

## How it works

- **Login** (`/login`) — demo only. Clicking **Login** navigates
  straight to `/dashboard`; no credentials are checked, nothing is
  sent anywhere.
- **Dashboard** (`/dashboard`) — current balance, total income/
  expenses, this month's and today's expenses, an expense-by-category
  chart, an income-vs-expense chart, and the 5 most recent
  transactions.
- **Transactions** (`/transactions`) — the full transaction list with
  type/category/date filters and delete.
- **Reports** (`/reports`) — Daily / Monthly / Yearly tabs, each with
  its own summary, charts, and transaction list.

All calculations (balance, daily/monthly/yearly summaries, category
totals) live in `src/utils/calculations.js` as small, reusable, pure
functions — no component re-implements the math.

## Data & storage

On first load, if `localStorage` has no BudgetNest data yet, the app
seeds itself with realistic mock transactions spanning about 19
months (`src/data/mockData.js`) so daily, monthly, and yearly reports
all have something to show immediately.

Everything after that is read from / written to two `localStorage`
keys (`src/utils/storage.js`):

```
budgetnest_transactions
budgetnest_starting_balance
```

Adding or deleting a transaction updates React state and
`localStorage` together, so the whole app (balances, charts, tables)
updates instantly with no page reload, and survives a refresh.

Use **Reset Demo Data** (bottom of the Dashboard) at any time to wipe
your changes and restore the original mock data.

## Note on this build

This project was written by hand in an environment without npm
registry access, so `npm install` / `npm run build` have **not** been
run or verified here — please run them locally as the first step.
The code follows standard Vite + React + Tailwind conventions closely,
but if `npm run build` surfaces anything, it'll most likely be a
minor dependency-version mismatch, easy to fix by adjusting the
version in `package.json`.
