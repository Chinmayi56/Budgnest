import React from "react";
import { formatCurrency } from "../utils/formatters.js";

const TONE_STYLES = {
  brand: { icon: "bg-brand-50 text-brand-600", value: "text-ink" },
  income: { icon: "bg-income-soft text-income", value: "text-income" },
  expense: { icon: "bg-expense-soft text-expense", value: "text-expense" },
  neutral: { icon: "bg-paper text-ink/60", value: "text-ink" },
};

export default function StatCard({ label, amount, icon: Icon, tone = "neutral", caption }) {
  const styles = TONE_STYLES[tone] || TONE_STYLES.neutral;

  return (
    <div className="bg-surface rounded-xl2 border border-border shadow-card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-ink/60">{label}</span>
        {Icon && (
          <span className={`h-9 w-9 rounded-lg flex items-center justify-center ${styles.icon}`}>
            <Icon size={18} />
          </span>
        )}
      </div>
      <div>
        <p className={`text-2xl font-display font-semibold ${styles.value}`}>
          {formatCurrency(amount)}
        </p>
        {caption && <p className="text-xs text-ink/45 mt-1">{caption}</p>}
      </div>
    </div>
  );
}
