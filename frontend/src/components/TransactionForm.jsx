import React, { useState } from "react";
import { X } from "lucide-react";
import { categoriesForType } from "../data/categories.js";
import { todayISO } from "../utils/formatters.js";
import { useFinance } from "../context/FinanceContext.jsx";

export default function TransactionForm({ onClose }) {
  const { addTransaction } = useFinance();
  const [type, setType] = useState("expense");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState(categoriesForType("expense")[0]);
  const [description, setDescription] = useState("");
  const [date, setDate] = useState(todayISO());
  const [error, setError] = useState("");

  const handleTypeChange = (nextType) => {
    setType(nextType);
    setCategory(categoriesForType(nextType)[0]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const numericAmount = Number(amount);
    if (!numericAmount || numericAmount <= 0) {
      setError("Enter an amount greater than zero.");
      return;
    }
    if (!date) {
      setError("Pick a date for this transaction.");
      return;
    }

    addTransaction({
      type,
      amount: numericAmount,
      category,
      description: description.trim() || category,
      date,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} aria-hidden="true" />

      <div className="relative w-full sm:max-w-md bg-surface rounded-t-2xl sm:rounded-xl2 shadow-card p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-display font-semibold text-ink">Add Transaction</h2>
          <button
            onClick={onClose}
            className="text-ink/40 hover:text-ink"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-2 bg-paper p-1 rounded-lg">
            {["expense", "income"].map((t) => (
              <button
                type="button"
                key={t}
                onClick={() => handleTypeChange(t)}
                className={`py-2 rounded-md text-sm font-medium capitalize transition-colors ${
                  type === t
                    ? t === "income"
                      ? "bg-income text-white"
                      : "bg-expense text-white"
                    : "text-ink/60 hover:text-ink"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <div>
            <label className="block text-sm font-medium text-ink/70 mb-1.5">Amount (₹)</label>
            <input
              type="number"
              inputMode="decimal"
              min="0"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="w-full rounded-lg border border-border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink/70 mb-1.5">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-300"
            >
              {categoriesForType(type).map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-ink/70 mb-1.5">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional note"
              className="w-full rounded-lg border border-border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink/70 mb-1.5">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            />
          </div>

          {error && <p className="text-sm text-expense">{error}</p>}

          <button
            type="submit"
            className="w-full bg-brand-500 hover:bg-brand-600 text-white font-medium py-2.5 rounded-lg transition-colors"
          >
            Add {type === "income" ? "Income" : "Expense"}
          </button>
        </form>
      </div>
    </div>
  );
}
