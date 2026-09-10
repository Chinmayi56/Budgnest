import React, { useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Plus, HandCoins, ArrowDownToLine, Scale } from "lucide-react";
import Header from "../components/Header.jsx";
import StatCard from "../components/StatCard.jsx";
import EstimationForm from "../components/EstimationForm.jsx";
import EstimationCard from "../components/EstimationCard.jsx";
import { useFinance } from "../context/FinanceContext.jsx";
import { calculateEstimationTotals } from "../utils/calculations.js";

export default function Estimation() {
  const { openSidebar } = useOutletContext();
  const { estimations, deleteEstimation, recordRefund, loadEstimationRefunds } = useFinance();
  const [showForm, setShowForm] = useState(false);

  const totals = useMemo(() => calculateEstimationTotals(estimations), [estimations]);

  const sorted = useMemo(
    () => [...estimations].sort((a, b) => (a.date < b.date ? 1 : -1)),
    [estimations]
  );

  return (
    <>
      <Header
        title="Estimation"
        subtitle="Track money you've lent and what's still outstanding"
        onMenuClick={openSidebar}
      />

      <main className="flex-1 px-4 sm:px-6 py-6 space-y-5 max-w-7xl w-full mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="Total Estimation" amount={totals.totalEstimation} icon={HandCoins} tone="brand" />
          <StatCard
            label="Total Refund"
            amount={totals.totalRefund}
            icon={ArrowDownToLine}
            tone="income"
          />
          <StatCard
            label="Outstanding Amount"
            amount={totals.totalOutstanding}
            icon={Scale}
            tone="expense"
          />
        </div>

        <div className="flex justify-end">
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-3.5 py-2 rounded-lg shadow-sm transition-colors"
          >
            <Plus size={16} />
            Add Estimation
          </button>
        </div>

        {sorted.length === 0 ? (
          <div className="text-center py-16 text-sm text-ink/45">
            No estimations yet — add the first one above.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {sorted.map((record) => (
              <EstimationCard
                key={record.id}
                record={record}
                onRecordRefund={recordRefund}
                onDelete={deleteEstimation}
                onLoadRefundHistory={loadEstimationRefunds}
              />
            ))}
          </div>
        )}
      </main>

      {showForm && <EstimationForm onClose={() => setShowForm(false)} />}
    </>
  );
}
