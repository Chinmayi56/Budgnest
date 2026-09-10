import React, { useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import Header from "../components/Header.jsx";
import TransactionForm from "../components/TransactionForm.jsx";
import TransactionTable from "../components/TransactionTable.jsx";
import ExportButtons from "../components/ExportButtons.jsx";
import { useFinance } from "../context/FinanceContext.jsx";
import { INCOME_CATEGORIES, EXPENSE_CATEGORIES } from "../data/categories.js";
import { sortByDateDesc } from "../utils/calculations.js";
import { todayISO } from "../utils/formatters.js";

const TYPE_TABS = [
  { value: "all", label: "All" },
  { value: "income", label: "Income" },
  { value: "expense", label: "Expense" },
];

export default function Transactions() {
  const { openSidebar } = useOutletContext();
  const { transactions, deleteTransaction } = useFinance();

  const [showForm, setShowForm] = useState(false);
  const [typeFilter, setTypeFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const availableCategories = useMemo(() => {
    if (typeFilter === "income") return INCOME_CATEGORIES;
    if (typeFilter === "expense") return EXPENSE_CATEGORIES;
    return [...new Set([...INCOME_CATEGORIES, ...EXPENSE_CATEGORIES])];
  }, [typeFilter]);

  const filtered = useMemo(() => {
    let list = sortByDateDesc(transactions);
    if (typeFilter !== "all") list = list.filter((t) => t.type === typeFilter);
    if (categoryFilter !== "all") list = list.filter((t) => t.category === categoryFilter);
    if (fromDate) list = list.filter((t) => t.date >= fromDate);
    if (toDate) list = list.filter((t) => t.date <= toDate);
    return list;
  }, [transactions, typeFilter, categoryFilter, fromDate, toDate]);

  const handleTypeChange = (value) => {
    setTypeFilter(value);
    setCategoryFilter("all");
  };

  const exportSummary = useMemo(() => {
    const income = filtered.filter((t) => t.type === "income").reduce((s, t) => s + t.amount, 0);
    const expenses = filtered.filter((t) => t.type === "expense").reduce((s, t) => s + t.amount, 0);
    return [
      { label: "Income", value: income },
      { label: "Expenses", value: expenses },
      { label: "Net", value: income - expenses },
    ];
  }, [filtered]);

  return (
    <>
      <Header
        title="Transactions"
        subtitle={`${filtered.length} of ${transactions.length} transactions`}
        onMenuClick={openSidebar}
        onAddTransaction={() => setShowForm(true)}
      />

      <main className="flex-1 px-4 sm:px-6 py-6 space-y-4 max-w-7xl w-full mx-auto">
        <div className="bg-surface rounded-xl2 border border-border shadow-card p-4 flex flex-wrap items-center gap-3">
          <div className="flex bg-paper p-1 rounded-lg">
            {TYPE_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => handleTypeChange(tab.value)}
                className={`px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  typeFilter === tab.value
                    ? "bg-brand-500 text-white"
                    : "text-ink/60 hover:text-ink"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="rounded-lg border border-border px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-300"
          >
            <option value="all">All Categories</option>
            {availableCategories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-2 text-sm text-ink/60">
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="rounded-lg border border-border px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            />
            <span>to</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="rounded-lg border border-border px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            />
          </div>

          {(typeFilter !== "all" || categoryFilter !== "all" || fromDate || toDate) && (
            <button
              onClick={() => {
                setTypeFilter("all");
                setCategoryFilter("all");
                setFromDate("");
                setToDate("");
              }}
              className="text-sm font-medium text-ink/45 hover:text-ink/70 ml-auto"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
          <div className="flex items-center justify-between gap-3 mb-3">
            <h2 className="text-sm font-semibold text-ink/80">Transactions</h2>
            <ExportButtons
              transactions={filtered}
              title="BudgetNest — Transactions"
              subtitle={`Exported ${todayISO()} — ${filtered.length} transaction${filtered.length === 1 ? "" : "s"}`}
              summary={exportSummary}
              filenameBase="budgetnest-transactions"
            />
          </div>
          <TransactionTable
            transactions={filtered}
            onDelete={deleteTransaction}
            emptyMessage="No transactions match these filters."
          />
        </div>
      </main>

      {showForm && <TransactionForm onClose={() => setShowForm(false)} />}
    </>
  );
}
