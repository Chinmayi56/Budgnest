// All transaction dates are plain "YYYY-MM-DD" strings, so month/year
// filtering is done with cheap, timezone-safe string comparisons
// instead of parsing into Date objects.

export function calculateTotalIncome(transactions) {
  return transactions
    .filter((t) => t.type === "income")
    .reduce((sum, t) => sum + Number(t.amount), 0);
}

export function calculateTotalExpenses(transactions) {
  return transactions
    .filter((t) => t.type === "expense")
    .reduce((sum, t) => sum + Number(t.amount), 0);
}

export function calculateCurrentBalance(startingBalance, transactions) {
  const income = calculateTotalIncome(transactions);
  const expenses = calculateTotalExpenses(transactions);
  return Number(startingBalance) + income - expenses;
}

function monthKey(year, month) {
  return `${year}-${String(month).padStart(2, "0")}`;
}

export function transactionsForDate(transactions, dateISO) {
  return transactions.filter((t) => t.date === dateISO);
}

export function transactionsForMonth(transactions, month, year) {
  const key = monthKey(year, month);
  return transactions.filter((t) => t.date.slice(0, 7) === key);
}

export function transactionsForYear(transactions, year) {
  const key = String(year);
  return transactions.filter((t) => t.date.slice(0, 4) === key);
}

export function calculateDailySummary(transactions, dateISO) {
  const dayTx = transactionsForDate(transactions, dateISO);
  const income = calculateTotalIncome(dayTx);
  const expenses = calculateTotalExpenses(dayTx);
  return {
    date: dateISO,
    income,
    expenses,
    net: income - expenses,
    transactions: dayTx,
  };
}

export function calculateMonthlySummary(transactions, month, year) {
  const monthTx = transactionsForMonth(transactions, month, year);
  const income = calculateTotalIncome(monthTx);
  const expenses = calculateTotalExpenses(monthTx);
  return {
    month,
    year,
    income,
    expenses,
    net: income - expenses,
    transactions: monthTx,
  };
}

export function calculateYearlySummary(transactions, year) {
  const yearTx = transactionsForYear(transactions, year);
  const income = calculateTotalIncome(yearTx);
  const expenses = calculateTotalExpenses(yearTx);

  const monthlyBreakdown = Array.from({ length: 12 }, (_, i) => {
    const month = i + 1;
    const summary = calculateMonthlySummary(transactions, month, year);
    return {
      month,
      income: summary.income,
      expenses: summary.expenses,
      net: summary.net,
    };
  });

  return {
    year,
    income,
    expenses,
    net: income - expenses,
    transactions: yearTx,
    monthlyBreakdown,
  };
}

/**
 * Groups expense totals by category for a given list of transactions
 * (already pre-filtered by whatever period the caller cares about).
 * Returns an array sorted from largest to smallest, ready for charts.
 */
export function calculateCategoryExpenses(transactions) {
  const totals = {};
  transactions
    .filter((t) => t.type === "expense")
    .forEach((t) => {
      totals[t.category] = (totals[t.category] || 0) + Number(t.amount);
    });

  return Object.entries(totals)
    .map(([category, amount]) => ({ category, amount }))
    .sort((a, b) => b.amount - a.amount);
}

export function sortByDateDesc(transactions) {
  return [...transactions].sort((a, b) => (a.date < b.date ? 1 : -1));
}

// ---------------------------------------------------------------------
// Bills & Reminders
// ---------------------------------------------------------------------

function daysBetween(fromISO, toISO) {
  const [fy, fm, fd] = fromISO.split("-").map(Number);
  const [ty, tm, td] = toISO.split("-").map(Number);
  const from = Date.UTC(fy, fm - 1, fd);
  const to = Date.UTC(ty, tm - 1, td);
  return Math.round((to - from) / (1000 * 60 * 60 * 24));
}

/**
 * Classifies a bill's reminder status relative to todayISO.
 * Returns one of: "paid", "overdue", "due-today", "upcoming".
 */
export function getBillReminderStatus(bill, todayISO) {
  if (bill.status === "paid") {
    return { status: "paid", daysUntil: null };
  }
  const daysUntil = daysBetween(todayISO, bill.dueDate);
  if (daysUntil < 0) return { status: "overdue", daysUntil };
  if (daysUntil === 0) return { status: "due-today", daysUntil };
  return { status: "upcoming", daysUntil };
}

/**
 * Groups bills into Overdue / Due Today / Upcoming / Paid buckets,
 * each sorted by due date (soonest first).
 */
export function groupBillsByStatus(bills, todayISO) {
  const groups = { overdue: [], dueToday: [], upcoming: [], paid: [] };

  bills.forEach((bill) => {
    const { status } = getBillReminderStatus(bill, todayISO);
    if (status === "paid") groups.paid.push(bill);
    else if (status === "overdue") groups.overdue.push(bill);
    else if (status === "due-today") groups.dueToday.push(bill);
    else groups.upcoming.push(bill);
  });

  const byDueDate = (a, b) => (a.dueDate < b.dueDate ? -1 : 1);
  groups.overdue.sort(byDueDate);
  groups.upcoming.sort(byDueDate);
  groups.paid.sort((a, b) => (a.paidDate < b.paidDate ? 1 : -1));

  return groups;
}

/**
 * Flat list of unpaid bills (overdue, due today, upcoming) sorted by
 * urgency, for the Reminders view.
 */
export function getBillReminders(bills, todayISO) {
  return bills
    .filter((b) => b.status !== "paid")
    .map((bill) => ({ bill, ...getBillReminderStatus(bill, todayISO) }))
    .sort((a, b) => a.daysUntil - b.daysUntil);
}

// ---------------------------------------------------------------------
// Estimation (refunds/installments)
// ---------------------------------------------------------------------

export function calculateRefundedAmount(record) {
  return (record.returns || []).reduce((sum, r) => sum + Number(r.amount), 0);
}

export function calculateOutstandingAmount(record) {
  return Number(record.amount) - calculateRefundedAmount(record);
}

/**
 * Aggregates Estimation / Refund / Outstanding totals across all
 * Estimation records.
 */
export function calculateEstimationTotals(records) {
  return records.reduce(
    (acc, record) => {
      const refunded = calculateRefundedAmount(record);
      acc.totalEstimation += Number(record.amount);
      acc.totalRefund += refunded;
      acc.totalOutstanding += Number(record.amount) - refunded;
      return acc;
    },
    { totalEstimation: 0, totalRefund: 0, totalOutstanding: 0 }
  );
}
