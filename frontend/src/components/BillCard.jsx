import React, { useState } from "react";
import { CheckCircle2, Trash2 } from "lucide-react";
import { formatCurrency, formatDate, formatReminderLabel, todayISO } from "../utils/formatters.js";
import { getBillReminderStatus } from "../utils/calculations.js";

const STATUS_STYLES = {
  overdue: "bg-expense-soft text-expense",
  "due-today": "bg-amber-100 text-amber-700",
  upcoming: "bg-brand-50 text-brand-600",
  paid: "bg-income-soft text-income",
};

export default function BillCard({ bill, onMarkPaid, onDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const { status, daysUntil } = getBillReminderStatus(bill, todayISO());

  return (
    <div className="flex items-center justify-between gap-3 py-3 px-4 rounded-lg border border-border bg-surface">
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink truncate">{bill.name}</p>
        <p className="text-xs text-ink/50 mt-0.5">
          {bill.category} &middot; Due {formatDate(bill.dueDate)}
        </p>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <span
          className={`text-xs font-medium px-2 py-1 rounded-full whitespace-nowrap ${STATUS_STYLES[status]}`}
        >
          {formatReminderLabel(status, daysUntil)}
        </span>
        <span className="text-sm font-semibold text-ink w-20 text-right">
          {formatCurrency(bill.amount)}
        </span>

        {bill.status !== "paid" && onMarkPaid && (
          <button
            onClick={() => onMarkPaid(bill.id)}
            className="flex items-center gap-1 text-xs font-medium text-income hover:text-income/80"
          >
            <CheckCircle2 size={15} />
            <span className="hidden sm:inline">Mark Paid</span>
          </button>
        )}

        {onDelete &&
          (confirmDelete ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onDelete(bill.id)}
                className="text-xs font-medium text-expense hover:underline"
              >
                Confirm
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="text-xs font-medium text-ink/50 hover:underline"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="text-ink/35 hover:text-expense transition-colors"
              aria-label="Delete bill"
            >
              <Trash2 size={16} />
            </button>
          ))}
      </div>
    </div>
  );
}
