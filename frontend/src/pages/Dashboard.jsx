import React, { useMemo, useState } from "react";
import { useOutletContext, useNavigate } from "react-router-dom";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  CalendarDays,
  CalendarRange,
  RotateCcw,
  AlertCircle,
  CalendarClock,
  HandCoins,
} from "lucide-react";
import Header from "../components/Header.jsx";
import StatCard from "../components/StatCard.jsx";
import TransactionForm from "../components/TransactionForm.jsx";
import TransactionTable from "../components/TransactionTable.jsx";
import CategoryPieChart from "../components/charts/CategoryPieChart.jsx";
import IncomeExpenseBarChart from "../components/charts/IncomeExpenseBarChart.jsx";
import { useFinance } from "../context/FinanceContext.jsx";
import {
  calculateCategoryExpenses,
  calculateMonthlySummary,
  sortByDateDesc,
} from "../utils/calculations.js";
import { formatMonthYear, formatCurrency } from "../utils/formatters.js";

export default function Dashboard() {
  const { openSidebar } = useOutletContext();
  const navigate = useNavigate();
  const {
    transactions,
    currentBalance,
    totalIncome,
    totalExpenses,
    monthExpenses,
    todayExpenses,
    upcomingBillsCount,
    overdueBillsCount,
    outstandingEstimation,
    deleteTransaction,
    resetDemoData,
  } = useFinance();

  const [showForm, setShowForm] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  const now = new Date();
  const monthLabel = formatMonthYear(now.getMonth() + 1, now.getFullYear());

  const monthSummary = useMemo(
    () => calculateMonthlySummary(transactions, now.getMonth() + 1, now.getFullYear()),
    [transactions]
  );

  const categoryData = useMemo(
    () => calculateCategoryExpenses(monthSummary.transactions),
    [monthSummary]
  );

  const recentTransactions = useMemo(
    () => sortByDateDesc(transactions).slice(0, 5),
    [transactions]
  );

  const handleReset = () => {
    resetDemoData();
    setConfirmReset(false);
  };

  return (
    <>
      <Header
        title="Dashboard"
        subtitle="Your finances at a glance"
        onMenuClick={openSidebar}
        onAddTransaction={() => setShowForm(true)}
      />

      <main className="flex-1 px-4 sm:px-6 py-6 space-y-6 max-w-7xl w-full mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
          <StatCard label="Current Balance" amount={currentBalance} icon={Wallet} tone="brand" />
          <StatCard label="Total Income" amount={totalIncome} icon={TrendingUp} tone="income" />
          <StatCard label="Total Expenses" amount={totalExpenses} icon={TrendingDown} tone="expense" />
          <StatCard
            label="This Month"
            amount={monthExpenses}
            icon={CalendarRange}
            tone="neutral"
            caption={monthLabel}
          />
          <StatCard
            label="Today's Expenses"
            amount={todayExpenses}
            icon={CalendarDays}
            tone="neutral"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
            <h2 className="text-sm font-semibold text-ink/80 mb-2">
              Expenses by Category <span className="text-ink/40 font-normal">— {monthLabel}</span>
            </h2>
            <CategoryPieChart data={categoryData} />
          </div>
          <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
            <h2 className="text-sm font-semibold text-ink/80 mb-2">
              Income vs Expenses <span className="text-ink/40 font-normal">— {monthLabel}</span>
            </h2>
            <IncomeExpenseBarChart income={monthSummary.income} expenses={monthSummary.expenses} />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <button
            onClick={() => navigate("/bills")}
            className="bg-surface rounded-xl2 border border-border shadow-card p-4 flex items-center gap-3 text-left hover:border-brand-300 transition-colors"
          >
            <span className="h-9 w-9 rounded-lg bg-expense-soft text-expense flex items-center justify-center shrink-0">
              <AlertCircle size={18} />
            </span>
            <span>
              <span className="block text-lg font-display font-semibold text-ink">
                {overdueBillsCount}
              </span>
              <span className="block text-xs text-ink/50">Overdue Bills</span>
            </span>
          </button>

          <button
            onClick={() => navigate("/bills")}
            className="bg-surface rounded-xl2 border border-border shadow-card p-4 flex items-center gap-3 text-left hover:border-brand-300 transition-colors"
          >
            <span className="h-9 w-9 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center shrink-0">
              <CalendarClock size={18} />
            </span>
            <span>
              <span className="block text-lg font-display font-semibold text-ink">
                {upcomingBillsCount}
              </span>
              <span className="block text-xs text-ink/50">Upcoming Bills</span>
            </span>
          </button>

          <button
            onClick={() => navigate("/estimation")}
            className="bg-surface rounded-xl2 border border-border shadow-card p-4 flex items-center gap-3 text-left hover:border-brand-300 transition-colors"
          >
            <span className="h-9 w-9 rounded-lg bg-paper text-ink/60 flex items-center justify-center shrink-0">
              <HandCoins size={18} />
            </span>
            <span>
              <span className="block text-lg font-display font-semibold text-ink">
                {formatCurrency(outstandingEstimation)}
              </span>
              <span className="block text-xs text-ink/50">Outstanding Estimation</span>
            </span>
          </button>
        </div>

        <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-ink/80">Recent Transactions</h2>
            <button
              onClick={() => navigate("/transactions")}
              className="text-sm font-medium text-brand-500 hover:text-brand-600"
            >
              View All
            </button>
          </div>
          <TransactionTable
            transactions={recentTransactions}
            onDelete={deleteTransaction}
            emptyMessage="No transactions yet — add your first one above."
          />
        </div>

        <div className="flex justify-center pt-2 pb-6">
          {confirmReset ? (
            <div className="flex items-center gap-3 text-sm bg-surface border border-border rounded-lg px-4 py-2.5 shadow-card">
              <span className="text-ink/70">Reload your data from the server?</span>
              <button onClick={handleReset} className="font-medium text-brand-600 hover:underline">
                Confirm
              </button>
              <button
                onClick={() => setConfirmReset(false)}
                className="font-medium text-ink/50 hover:underline"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmReset(true)}
              className="flex items-center gap-1.5 text-sm text-ink/45 hover:text-ink/70 transition-colors"
            >
              <RotateCcw size={14} />
              Refresh Data
            </button>
          )}
        </div>
      </main>

      {showForm && <TransactionForm onClose={() => setShowForm(false)} />}
    </>
  );
}
