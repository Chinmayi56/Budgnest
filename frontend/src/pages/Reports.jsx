import React, { useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { TrendingUp, TrendingDown, Scale } from "lucide-react";
import Header from "../components/Header.jsx";
import StatCard from "../components/StatCard.jsx";
import TransactionTable from "../components/TransactionTable.jsx";
import ExportButtons from "../components/ExportButtons.jsx";
import CategoryPieChart from "../components/charts/CategoryPieChart.jsx";
import IncomeExpenseBarChart from "../components/charts/IncomeExpenseBarChart.jsx";
import MonthlyTrendChart from "../components/charts/MonthlyTrendChart.jsx";
import { useFinance } from "../context/FinanceContext.jsx";
import {
  calculateDailySummary,
  calculateMonthlySummary,
  calculateYearlySummary,
  calculateCategoryExpenses,
  sortByDateDesc,
} from "../utils/calculations.js";
import { formatMonthYear, formatDate, MONTH_NAMES, todayISO } from "../utils/formatters.js";

const TABS = [
  { value: "daily", label: "Daily" },
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
];

export default function Reports() {
  const { openSidebar } = useOutletContext();
  const { transactions, deleteTransaction } = useFinance();
  const now = new Date();

  const [tab, setTab] = useState("daily");
  const [selectedDate, setSelectedDate] = useState(todayISO());
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(now.getFullYear());
  const [selectedYearlyYear, setSelectedYearlyYear] = useState(now.getFullYear());

  const yearOptions = useMemo(() => {
    const years = new Set(transactions.map((t) => Number(t.date.slice(0, 4))));
    years.add(now.getFullYear());
    return [...years].sort((a, b) => b - a);
  }, [transactions]);

  const dailySummary = useMemo(
    () => calculateDailySummary(transactions, selectedDate),
    [transactions, selectedDate]
  );

  const monthlySummary = useMemo(
    () => calculateMonthlySummary(transactions, selectedMonth, selectedYear),
    [transactions, selectedMonth, selectedYear]
  );

  const monthlyCategoryData = useMemo(
    () => calculateCategoryExpenses(monthlySummary.transactions),
    [monthlySummary]
  );

  const yearlySummary = useMemo(
    () => calculateYearlySummary(transactions, selectedYearlyYear),
    [transactions, selectedYearlyYear]
  );

  return (
    <>
      <Header title="Reports" subtitle="Daily, monthly, and yearly breakdowns" onMenuClick={openSidebar} />

      <main className="flex-1 px-4 sm:px-6 py-6 space-y-5 max-w-7xl w-full mx-auto">
        <div className="flex bg-paper p-1 rounded-lg w-fit">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === t.value ? "bg-brand-500 text-white" : "text-ink/60 hover:text-ink"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "daily" && (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-ink/60">Date</label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="rounded-lg border border-border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard label="Today's Income" amount={dailySummary.income} icon={TrendingUp} tone="income" />
              <StatCard label="Today's Expenses" amount={dailySummary.expenses} icon={TrendingDown} tone="expense" />
              <StatCard label="Net Amount" amount={dailySummary.net} icon={Scale} tone="brand" />
            </div>

            <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
              <div className="flex items-center justify-between gap-3 mb-2">
                <h2 className="text-sm font-semibold text-ink/80">Transactions</h2>
                <ExportButtons
                  transactions={sortByDateDesc(dailySummary.transactions)}
                  title="BudgetNest — Daily Report"
                  subtitle={formatDate(selectedDate)}
                  summary={[
                    { label: "Income", value: dailySummary.income },
                    { label: "Expenses", value: dailySummary.expenses },
                    { label: "Net", value: dailySummary.net },
                  ]}
                  filenameBase={`budgetnest-daily-${selectedDate}`}
                />
              </div>
              <TransactionTable
                transactions={sortByDateDesc(dailySummary.transactions)}
                onDelete={deleteTransaction}
                emptyMessage="No transactions on this date."
              />
            </div>
          </div>
        )}

        {tab === "monthly" && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-sm font-medium text-ink/60">Month</label>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                className="rounded-lg border border-border px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-300"
              >
                {MONTH_NAMES.map((name, i) => (
                  <option key={name} value={i + 1}>
                    {name}
                  </option>
                ))}
              </select>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="rounded-lg border border-border px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-300"
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
              <span className="text-sm text-ink/40">{formatMonthYear(selectedMonth, selectedYear)}</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard label="Monthly Income" amount={monthlySummary.income} icon={TrendingUp} tone="income" />
              <StatCard label="Monthly Expenses" amount={monthlySummary.expenses} icon={TrendingDown} tone="expense" />
              <StatCard label="Net Amount" amount={monthlySummary.net} icon={Scale} tone="brand" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
                <h2 className="text-sm font-semibold text-ink/80 mb-2">Expense Category Breakdown</h2>
                <CategoryPieChart data={monthlyCategoryData} />
              </div>
              <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
                <h2 className="text-sm font-semibold text-ink/80 mb-2">Income vs Expense</h2>
                <IncomeExpenseBarChart income={monthlySummary.income} expenses={monthlySummary.expenses} />
              </div>
            </div>

            <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
              <div className="flex items-center justify-between gap-3 mb-2">
                <h2 className="text-sm font-semibold text-ink/80">Transactions</h2>
                <ExportButtons
                  transactions={sortByDateDesc(monthlySummary.transactions)}
                  title="BudgetNest — Monthly Report"
                  subtitle={formatMonthYear(selectedMonth, selectedYear)}
                  summary={[
                    { label: "Income", value: monthlySummary.income },
                    { label: "Expenses", value: monthlySummary.expenses },
                    { label: "Net", value: monthlySummary.net },
                  ]}
                  filenameBase={`budgetnest-monthly-${selectedYear}-${String(selectedMonth).padStart(2, "0")}`}
                />
              </div>
              <TransactionTable
                transactions={sortByDateDesc(monthlySummary.transactions)}
                onDelete={deleteTransaction}
                emptyMessage="No transactions in this month."
              />
            </div>
          </div>
        )}

        {tab === "yearly" && (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-ink/60">Year</label>
              <select
                value={selectedYearlyYear}
                onChange={(e) => setSelectedYearlyYear(Number(e.target.value))}
                className="rounded-lg border border-border px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-300"
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard label="Yearly Income" amount={yearlySummary.income} icon={TrendingUp} tone="income" />
              <StatCard label="Yearly Expenses" amount={yearlySummary.expenses} icon={TrendingDown} tone="expense" />
              <StatCard label="Net Amount" amount={yearlySummary.net} icon={Scale} tone="brand" />
            </div>

            <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
              <h2 className="text-sm font-semibold text-ink/80 mb-2">Monthly Breakdown</h2>
              <MonthlyTrendChart monthlyBreakdown={yearlySummary.monthlyBreakdown} />
            </div>

            <div className="bg-surface rounded-xl2 border border-border shadow-card p-5 overflow-x-auto">
              <div className="flex items-center justify-between gap-3 mb-3">
                <h2 className="text-sm font-semibold text-ink/80">Month-by-Month</h2>
                <ExportButtons
                  transactions={sortByDateDesc(yearlySummary.transactions)}
                  title="BudgetNest — Yearly Report"
                  subtitle={`${selectedYearlyYear}`}
                  summary={[
                    { label: "Income", value: yearlySummary.income },
                    { label: "Expenses", value: yearlySummary.expenses },
                    { label: "Net", value: yearlySummary.net },
                  ]}
                  filenameBase={`budgetnest-yearly-${selectedYearlyYear}`}
                />
              </div>
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-ink/45 uppercase tracking-wide border-b border-border">
                    <th className="py-2 pr-4 font-medium">Month</th>
                    <th className="py-2 pr-4 font-medium text-right">Income</th>
                    <th className="py-2 pr-4 font-medium text-right">Expenses</th>
                    <th className="py-2 font-medium text-right">Net</th>
                  </tr>
                </thead>
                <tbody>
                  {yearlySummary.monthlyBreakdown.map((m) => (
                    <tr key={m.month} className="border-b border-border/70 last:border-0">
                      <td className="py-2 pr-4 text-ink/80">{MONTH_NAMES[m.month - 1]}</td>
                      <td className="py-2 pr-4 text-right text-income">
                        {m.income ? `₹${m.income.toLocaleString("en-IN")}` : "—"}
                      </td>
                      <td className="py-2 pr-4 text-right text-expense">
                        {m.expenses ? `₹${m.expenses.toLocaleString("en-IN")}` : "—"}
                      </td>
                      <td className="py-2 text-right font-medium text-ink">
                        ₹{m.net.toLocaleString("en-IN")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
