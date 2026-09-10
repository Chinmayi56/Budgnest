import React, { useState } from "react";
import { Trash2, Undo2, ChevronDown, ChevronUp } from "lucide-react";
import { formatCurrency, formatDate, todayISO } from "../utils/formatters.js";
import { calculateRefundedAmount, calculateOutstandingAmount } from "../utils/calculations.js";

export default function EstimationCard({ record, onRecordRefund, onDelete, onLoadRefundHistory }) {
  const [showRefundForm, setShowRefundForm] = useState(false);
  const [refundAmount, setRefundAmount] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const refunded = calculateRefundedAmount(record);
  const outstanding = calculateOutstandingAmount(record);
  const isFullyRefunded = outstanding <= 0;
  const hasRefunds = refunded > 0;

  const handleRefundSubmit = (e) => {
    e.preventDefault();
    const amount = Number(refundAmount);
    if (!amount || amount <= 0) return;
    onRecordRefund(record.id, amount, todayISO());
    setRefundAmount("");
    setShowRefundForm(false);
    // The next time history is opened, make sure it reflects the
    // refund that was just recorded.
    setHistoryLoaded(false);
  };

  const toggleHistory = async () => {
    const next = !showHistory;
    setShowHistory(next);
    if (next && !historyLoaded && onLoadRefundHistory) {
      await onLoadRefundHistory(record.id);
      setHistoryLoaded(true);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">{record.personName}</p>
          <p className="text-xs text-ink/50 mt-0.5">
            {formatDate(record.date)}
            {record.description ? ` · ${record.description}` : ""}
          </p>
        </div>
        {onDelete &&
          (confirmDelete ? (
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => onDelete(record.id)}
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
              className="text-ink/35 hover:text-expense transition-colors shrink-0"
              aria-label="Delete record"
            >
              <Trash2 size={16} />
            </button>
          ))}
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3 text-center">
        <div className="rounded-md bg-paper py-2">
          <p className="text-[11px] text-ink/45 uppercase tracking-wide">Estimation</p>
          <p className="text-sm font-semibold text-ink">{formatCurrency(record.amount)}</p>
        </div>
        <div className="rounded-md bg-paper py-2">
          <p className="text-[11px] text-ink/45 uppercase tracking-wide">Refund</p>
          <p className="text-sm font-semibold text-income">{formatCurrency(refunded)}</p>
        </div>
        <div className="rounded-md bg-paper py-2">
          <p className="text-[11px] text-ink/45 uppercase tracking-wide">Outstanding</p>
          <p className={`text-sm font-semibold ${isFullyRefunded ? "text-ink/40" : "text-expense"}`}>
            {formatCurrency(outstanding)}
          </p>
        </div>
      </div>

      {hasRefunds && (
        <div className="mt-3">
          <button
            onClick={toggleHistory}
            className="flex items-center gap-1 text-xs font-medium text-ink/55 hover:text-ink"
          >
            {showHistory ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            Refund History
          </button>
          {showHistory && (
            <div className="mt-2 rounded-md bg-paper p-3 space-y-1.5">
              {(record.returns || []).length === 0 ? (
                <p className="text-xs text-ink/45">Loading refund history…</p>
              ) : (
                <>
                  {(record.returns || [])
                    .slice()
                    .sort((a, b) => (a.date < b.date ? 1 : -1))
                    .map((r) => (
                      <div key={r.id} className="flex items-center justify-between text-xs">
                        <span className="text-ink/60">{formatDate(r.date)}</span>
                        <span className="font-medium text-income">{formatCurrency(r.amount)}</span>
                      </div>
                    ))}
                  <div className="border-t border-border pt-1.5 mt-1.5 flex items-center justify-between text-xs font-semibold">
                    <span className="text-ink/70">Total Refund</span>
                    <span className="text-income">{formatCurrency(refunded)}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-ink/70">Outstanding</span>
                    <span className={isFullyRefunded ? "text-ink/40" : "text-expense"}>
                      {formatCurrency(outstanding)}
                    </span>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {!isFullyRefunded && (
        <div className="mt-3">
          {showRefundForm ? (
            <form onSubmit={handleRefundSubmit} className="flex items-center gap-2">
              <input
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                max={outstanding}
                value={refundAmount}
                onChange={(e) => setRefundAmount(e.target.value)}
                placeholder={`Up to ${formatCurrency(outstanding)}`}
                autoFocus
                className="flex-1 rounded-lg border border-border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
              />
              <button
                type="button"
                onClick={() => setRefundAmount(String(outstanding))}
                className="text-xs font-medium text-brand-600 hover:underline whitespace-nowrap"
              >
                Full Amount
              </button>
              <button
                type="submit"
                className="bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium px-3 py-1.5 rounded-lg"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => setShowRefundForm(false)}
                className="text-xs font-medium text-ink/50 hover:underline"
              >
                Cancel
              </button>
            </form>
          ) : (
            <button
              onClick={() => setShowRefundForm(true)}
              className="flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700"
            >
              <Undo2 size={14} />
              Record Refund
            </button>
          )}
        </div>
      )}
    </div>
  );
}
