import React, { useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Plus, AlertCircle, Clock, CalendarClock, CheckCircle2 } from "lucide-react";
import Header from "../components/Header.jsx";
import BillForm from "../components/BillForm.jsx";
import BillCard from "../components/BillCard.jsx";
import { useFinance } from "../context/FinanceContext.jsx";
import { groupBillsByStatus, getBillReminders } from "../utils/calculations.js";
import { todayISO, formatReminderLabel } from "../utils/formatters.js";

const TABS = [
  { value: "bills", label: "Bills" },
  { value: "reminders", label: "Reminders" },
];

function Section({ title, icon: Icon, tone, bills, onMarkPaid, onDelete, emptyText }) {
  if (!bills.length) return null;
  return (
    <div>
      <h2 className={`flex items-center gap-1.5 text-sm font-semibold mb-2 ${tone}`}>
        <Icon size={16} />
        {title}
        <span className="text-ink/40 font-normal">({bills.length})</span>
      </h2>
      <div className="space-y-2">
        {bills.map((bill) => (
          <BillCard key={bill.id} bill={bill} onMarkPaid={onMarkPaid} onDelete={onDelete} />
        ))}
      </div>
    </div>
  );
}

export default function BillsPayments() {
  const { openSidebar } = useOutletContext();
  const { bills, markBillPaid, deleteBill } = useFinance();
  const [showForm, setShowForm] = useState(false);
  const [tab, setTab] = useState("bills");

  const today = todayISO();
  const groups = useMemo(() => groupBillsByStatus(bills, today), [bills, today]);
  const reminders = useMemo(() => getBillReminders(bills, today), [bills, today]);

  const hasAnyBills = bills.length > 0;

  return (
    <>
      <Header
        title="Bills & Payments"
        subtitle="Track upcoming, due, and paid bills"
        onMenuClick={openSidebar}
      />

      <main className="flex-1 px-4 sm:px-6 py-6 space-y-5 max-w-7xl w-full mx-auto">
        <div className="flex items-center justify-between flex-wrap gap-3">
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

          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-3.5 py-2 rounded-lg shadow-sm transition-colors"
          >
            <Plus size={16} />
            Add Bill
          </button>
        </div>

        {!hasAnyBills && (
          <div className="text-center py-16 text-sm text-ink/45">
            No bills yet — add your first bill above.
          </div>
        )}

        {hasAnyBills && tab === "bills" && (
          <div className="space-y-6">
            <Section
              title="Overdue Bills"
              icon={AlertCircle}
              tone="text-expense"
              bills={groups.overdue}
              onMarkPaid={markBillPaid}
              onDelete={deleteBill}
            />
            <Section
              title="Due Today"
              icon={Clock}
              tone="text-amber-700"
              bills={groups.dueToday}
              onMarkPaid={markBillPaid}
              onDelete={deleteBill}
            />
            <Section
              title="Upcoming Bills"
              icon={CalendarClock}
              tone="text-brand-600"
              bills={groups.upcoming}
              onMarkPaid={markBillPaid}
              onDelete={deleteBill}
            />
            <Section
              title="Paid Bills"
              icon={CheckCircle2}
              tone="text-income"
              bills={groups.paid}
              onDelete={deleteBill}
            />
          </div>
        )}

        {hasAnyBills && tab === "reminders" && (
          <div className="bg-surface rounded-xl2 border border-border shadow-card p-5">
            <h2 className="text-sm font-semibold text-ink/80 mb-3">Payment Reminders</h2>
            {reminders.length === 0 ? (
              <p className="text-sm text-ink/45 py-6 text-center">
                No pending reminders — all bills are paid.
              </p>
            ) : (
              <ul className="divide-y divide-border/70">
                {reminders.map(({ bill, status, daysUntil }) => (
                  <li key={bill.id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm font-medium text-ink">{bill.name}</p>
                      <p className="text-xs text-ink/50">₹{bill.amount.toLocaleString("en-IN")}</p>
                    </div>
                    <span
                      className={`text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${
                        status === "overdue"
                          ? "bg-expense-soft text-expense"
                          : status === "due-today"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-brand-50 text-brand-600"
                      }`}
                    >
                      {formatReminderLabel(status, daysUntil)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-xs text-ink/40 mt-4">
              This is a visual reminder list only — no notifications are sent.
            </p>
          </div>
        )}
      </main>

      {showForm && <BillForm onClose={() => setShowForm(false)} />}
    </>
  );
}
