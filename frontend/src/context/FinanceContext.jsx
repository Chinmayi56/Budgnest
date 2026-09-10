import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useLocation } from "react-router-dom";
import { api, getToken } from "../utils/api.js";
import {
  calculateTotalIncome,
  calculateTotalExpenses,
  calculateCurrentBalance,
  calculateDailySummary,
  calculateMonthlySummary,
  groupBillsByStatus,
  calculateEstimationTotals,
} from "../utils/calculations.js";
import { todayISO } from "../utils/formatters.js";

// ---------------------------------------------------------------------
// FinanceContext
//
// SECURITY NOTE (see FEATURE: USER-SPECIFIC DATA ISOLATION):
// All financial data (transactions, bills, estimation records,
// starting balance) is now loaded from — and written to — the
// authenticated backend API (see utils/api.js), never browser
// localStorage. The backend resolves the acting user from the JWT on
// every request and scopes every read/write to that user alone, so
// two different accounts signed into the same browser can never see
// or affect one another's data. This file only holds a client-side
// *cache* of the current user's own data for fast rendering; it is
// reloaded from the server whenever the signed-in user changes (see
// the token-tracking effect below), so switching accounts always
// starts from a clean slate instead of showing leftover data from
// whoever was previously signed in on this browser.
// ---------------------------------------------------------------------

const FinanceContext = createContext(null);

// --- Mapping helpers: backend document shape -> the shape every ------
// --- page/component in this app already expects. ---------------------

function mapTransaction(doc) {
  return {
    id: doc.id,
    type: doc.transaction_type === "INCOME" ? "income" : "expense",
    category: doc.category || "Other",
    amount: Number(doc.amount),
    description: doc.description || doc.category || "",
    date: doc.transaction_date,
  };
}

function mapBill(doc) {
  return {
    id: doc.id,
    name: doc.name,
    amount: Number(doc.amount),
    dueDate: doc.due_date,
    category: doc.category || "Other",
    status: doc.status === "COMPLETED" ? "paid" : "unpaid",
    paidDate: doc.last_paid_date || null,
    transactionId: doc.last_transaction_id || null,
  };
}

function mapEstimation(doc, previousReturns) {
  const returnedAmount = Number(doc.amount_returned || 0);
  // The list endpoint returns only running totals, not each
  // individual refund/installment. If we've already loaded the real
  // refund history for this record (via loadEstimationRefunds), keep
  // using it as long as it still adds up to the same total; otherwise
  // fall back to a single synthetic entry so totals
  // (calculateRefundedAmount / calculateOutstandingAmount, which just
  // sum record.returns[].amount) stay correct until the real history
  // is loaded.
  if (
    previousReturns &&
    previousReturns.reduce((sum, r) => sum + Number(r.amount), 0) === returnedAmount
  ) {
    return {
      id: doc.id,
      personName: doc.person_name,
      amount: Number(doc.amount_given),
      date: doc.given_date,
      description: doc.reason || "",
      returns: previousReturns,
    };
  }
  return {
    id: doc.id,
    personName: doc.person_name,
    amount: Number(doc.amount_given),
    date: doc.given_date,
    description: doc.reason || "",
    returns:
      returnedAmount > 0
        ? [{ id: `${doc.id}-refund`, amount: returnedAmount, date: doc.given_date }]
        : [],
  };
}

// Only transaction types this simplified UI ever needs to show as a
// line item: user-entered income/expense, plus bill payments (which
// the original app also always surfaced as an expense transaction).
// MONEY_GIVEN/MONEY_RETURNED (Estimation/Refund) are tracked
// separately (Estimation page) and were never mixed into the main
// transaction feed/balance math here, matching the app's original
// behavior.
function isDisplayableTransaction(doc) {
  if (doc.status === "CANCELLED") return false;
  return doc.transaction_type === "INCOME" || doc.transaction_type === "EXPENSE" || doc.transaction_type === "PAYMENT";
}

function isActiveBill(doc) {
  return doc.status === "ACTIVE" || doc.status === "COMPLETED";
}

function isActiveEstimation(doc) {
  return doc.status !== "CANCELLED";
}

export function FinanceProvider({ children }) {
  const location = useLocation();
  const [startingBalance, setStartingBalance] = useState(0);
  const [transactions, setTransactions] = useState([]);
  const [bills, setBills] = useState([]);
  const [estimations, setEstimations] = useState([]);
  const [ready, setReady] = useState(false);

  // Tracks which token's data is currently loaded, so we can tell a
  // fresh sign-in (or sign-out) apart from an ordinary route change.
  const loadedTokenRef = useRef(undefined);

  const loadAll = useCallback(async () => {
    setReady(false);
    try {
      const [balanceDoc, txDocs, billDocs, estimationDocs] = await Promise.all([
        api.getStartingBalance(),
        api.listAllTransactions(),
        api.listAllBills(),
        api.listAllEstimations(),
      ]);
      setStartingBalance(balanceDoc ? Number(balanceDoc.amount) : 0);
      setTransactions(txDocs.filter(isDisplayableTransaction).map(mapTransaction));
      setBills(billDocs.filter(isActiveBill).map(mapBill));
      setEstimations(estimationDocs.filter(isActiveEstimation).map((doc) => mapEstimation(doc)));
    } catch (err) {
      console.error("Failed to load your financial data:", err);
    } finally {
      setReady(true);
    }
  }, []);

  // Reload from the server whenever the signed-in user changes
  // (covers: fresh login, logout, and one account logging out and a
  // different one logging in on the same browser). Also fires on
  // every route change, which is cheap to check (just a token
  // comparison) and guarantees we never miss a transition.
  useEffect(() => {
    const token = getToken();
    if (token === loadedTokenRef.current) return;
    loadedTokenRef.current = token;

    if (!token) {
      setStartingBalance(0);
      setTransactions([]);
      setBills([]);
      setEstimations([]);
      setReady(false);
      return;
    }

    loadAll();
  }, [location.pathname, loadAll]);

  function reportError(err) {
    console.error(err);
    const message = err && err.message ? err.message : "Something went wrong. Please try again.";
    // Fire-and-forget callers (the Add* forms close immediately and
    // don't await these promises) still need some signal that the
    // save didn't actually happen server-side.
    window.alert(message);
  }

  // --- Transactions ---------------------------------------------------

  const addTransaction = useCallback(async (transaction) => {
    try {
      const doc = await api.createTransaction({
        transaction_type: transaction.type === "income" ? "INCOME" : "EXPENSE",
        amount: transaction.amount,
        category: transaction.category,
        description: transaction.description,
        transaction_date: transaction.date,
      });
      const mapped = mapTransaction(doc);
      setTransactions((prev) => [mapped, ...prev]);
      return mapped;
    } catch (err) {
      reportError(err);
      return null;
    }
  }, []);

  const deleteTransaction = useCallback(async (id) => {
    try {
      await api.cancelTransaction(id);
      setTransactions((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      reportError(err);
    }
  }, []);

  const updateStartingBalance = useCallback(async (amount) => {
    const value = Number(amount);
    try {
      let doc;
      try {
        doc = await api.adjustStartingBalance(value);
      } catch (err) {
        if (err && err.status === 404) {
          doc = await api.createStartingBalance(value, todayISO());
        } else {
          throw err;
        }
      }
      setStartingBalance(Number(doc.amount));
    } catch (err) {
      reportError(err);
    }
  }, []);

  // --- Bills & Payments -------------------------------------------------

  const addBill = useCallback(async (bill) => {
    try {
      const doc = await api.createBill({
        name: bill.name,
        amount: bill.amount,
        due_date: bill.dueDate,
        category: bill.category,
        is_recurring: false,
      });
      setBills((prev) => [mapBill(doc), ...prev]);
    } catch (err) {
      reportError(err);
    }
  }, []);

  const deleteBill = useCallback(async (id) => {
    try {
      await api.cancelBill(id);
      setBills((prev) => prev.filter((b) => b.id !== id));
    } catch (err) {
      reportError(err);
    }
  }, []);

  const markBillPaid = useCallback(async (id) => {
    try {
      const doc = await api.payBill(id, todayISO());
      setBills((prev) => prev.map((b) => (b.id === id ? mapBill(doc) : b)));
      if (doc.last_transaction_id) {
        setTransactions((prev) => [
          {
            id: doc.last_transaction_id,
            type: "expense",
            category: doc.category || "Other",
            amount: Number(doc.amount),
            description: `Bill payment: ${doc.name}`,
            date: doc.last_paid_date || todayISO(),
          },
          ...prev,
        ]);
      }
    } catch (err) {
      reportError(err);
    }
  }, []);

  // --- Estimation (refunds/installments) --------------------------------

  const addEstimation = useCallback(async (record) => {
    try {
      const doc = await api.createEstimation({
        person_name: record.personName,
        amount: record.amount,
        given_date: record.date,
        reason: record.description || undefined,
        notes: record.installments ? `Planned installments: ${record.installments}` : undefined,
      });
      setEstimations((prev) => [mapEstimation(doc), ...prev]);
    } catch (err) {
      reportError(err);
    }
  }, []);

  const deleteEstimation = useCallback(async (id) => {
    try {
      await api.cancelEstimation(id);
      setEstimations((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      reportError(err);
    }
  }, []);

  // Loads the individual refund/installment history for one
  // estimation from the backend (GET /money-given/{id}/returns) and
  // merges it into that record, replacing the synthetic single-entry
  // placeholder used until this has been called.
  const loadEstimationRefunds = useCallback(async (id) => {
    try {
      const res = await api.listRefunds(id);
      const mapped = (res.items || []).map((r) => ({
        id: r.id,
        amount: Number(r.amount),
        date: r.return_date,
        notes: r.notes || "",
      }));
      setEstimations((prev) => prev.map((r) => (r.id === id ? { ...r, returns: mapped } : r)));
      return mapped;
    } catch (err) {
      reportError(err);
      return [];
    }
  }, []);

  const recordRefund = useCallback(
    async (id, amount, date, notes) => {
      try {
        const doc = await api.addRefund(id, {
          amount: Number(amount),
          return_date: date || todayISO(),
          notes: notes || undefined,
        });
        setEstimations((prev) =>
          prev.map((r) => (r.id === id ? mapEstimation(doc, undefined) : r))
        );
        // Refresh the real refund history in the background so the
        // installment history shown on the card reflects every
        // individual refund, not just the running total.
        loadEstimationRefunds(id);
      } catch (err) {
        reportError(err);
      }
    },
    [loadEstimationRefunds]
  );

  // --- Refresh (was "reset to demo data" back when this app used a ---
  // --- local mock store; now it simply re-syncs with the server) -----

  const resetDemoData = useCallback(() => {
    loadAll();
  }, [loadAll]);

  // --- Derived totals ------------------------------------------------

  const totals = useMemo(() => {
    const totalIncome = calculateTotalIncome(transactions);
    const totalExpenses = calculateTotalExpenses(transactions);
    const currentBalance = calculateCurrentBalance(startingBalance, transactions);
    const today = todayISO();
    const now = new Date();
    const todaySummary = calculateDailySummary(transactions, today);
    const monthSummary = calculateMonthlySummary(
      transactions,
      now.getMonth() + 1,
      now.getFullYear()
    );

    const billGroups = groupBillsByStatus(bills, today);
    const estimationTotals = calculateEstimationTotals(estimations);

    return {
      totalIncome,
      totalExpenses,
      currentBalance,
      todayExpenses: todaySummary.expenses,
      monthExpenses: monthSummary.expenses,
      upcomingBillsCount: billGroups.upcoming.length,
      overdueBillsCount: billGroups.overdue.length,
      dueTodayBillsCount: billGroups.dueToday.length,
      outstandingEstimation: estimationTotals.totalOutstanding,
    };
  }, [transactions, startingBalance, bills, estimations]);

  const value = {
    ready,
    startingBalance,
    transactions,
    bills,
    estimations,
    addTransaction,
    deleteTransaction,
    updateStartingBalance,
    addBill,
    deleteBill,
    markBillPaid,
    addEstimation,
    deleteEstimation,
    recordRefund,
    loadEstimationRefunds,
    resetDemoData,
    ...totals,
  };

  return (
    <FinanceContext.Provider value={value}>{children}</FinanceContext.Provider>
  );
}

export function useFinance() {
  const ctx = useContext(FinanceContext);
  if (!ctx) {
    throw new Error("useFinance must be used within a FinanceProvider");
  }
  return ctx;
}
