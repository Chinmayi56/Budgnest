import React, { useState } from "react";
import { Trash2, ArrowDownCircle, ArrowUpCircle } from "lucide-react";
import { formatCurrency, formatDate } from "../utils/formatters.js";

export default function TransactionTable({ transactions, onDelete, emptyMessage }) {
  const [pendingDeleteId, setPendingDeleteId] = useState(null);

  if (!transactions.length) {
    return (
      <div className="text-center py-10 text-sm text-ink/45">
        {emptyMessage || "No transactions yet."}
      </div>
    );
  }

  const confirmDelete = (id) => {
    onDelete(id);
    setPendingDeleteId(null);
  };

  return (
    <div className="overflow-x-auto -mx-5 sm:mx-0">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-ink/45 uppercase tracking-wide border-b border-border">
            <th className="py-2.5 px-5 sm:px-3 font-medium">Type</th>
            <th className="py-2.5 px-3 font-medium">Category</th>
            <th className="py-2.5 px-3 font-medium hidden sm:table-cell">Description</th>
            <th className="py-2.5 px-3 font-medium">Date</th>
            <th className="py-2.5 px-3 font-medium text-right">Amount</th>
            {onDelete && (
              <th className="py-2.5 px-5 sm:px-3 font-medium text-right">
                <span className="sr-only">Actions</span>
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <tr key={t.id} className="border-b border-border/70 last:border-0 hover:bg-paper/60">
              <td className="py-3 px-5 sm:px-3">
                <span
                  className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full ${
                    t.type === "income"
                      ? "bg-income-soft text-income"
                      : "bg-expense-soft text-expense"
                  }`}
                >
                  {t.type === "income" ? (
                    <ArrowUpCircle size={13} />
                  ) : (
                    <ArrowDownCircle size={13} />
                  )}
                  {t.type === "income" ? "Income" : "Expense"}
                </span>
              </td>
              <td className="py-3 px-3 text-ink/80">{t.category}</td>
              <td className="py-3 px-3 text-ink/60 hidden sm:table-cell max-w-[220px] truncate">
                {t.description}
              </td>
              <td className="py-3 px-3 text-ink/60 whitespace-nowrap">{formatDate(t.date)}</td>
              <td
                className={`py-3 px-3 text-right font-medium whitespace-nowrap ${
                  t.type === "income" ? "text-income" : "text-expense"
                }`}
              >
                {t.type === "income" ? "+" : "-"}
                {formatCurrency(t.amount)}
              </td>
              {onDelete && (
                <td className="py-3 px-5 sm:px-3 text-right">
                  {pendingDeleteId === t.id ? (
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => confirmDelete(t.id)}
                        className="text-xs font-medium text-expense hover:underline"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => setPendingDeleteId(null)}
                        className="text-xs font-medium text-ink/50 hover:underline"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setPendingDeleteId(t.id)}
                      className="text-ink/35 hover:text-expense transition-colors"
                      aria-label="Delete transaction"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
