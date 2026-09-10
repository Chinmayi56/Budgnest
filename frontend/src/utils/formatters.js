const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export function formatCurrency(amount) {
  const value = Number.isFinite(amount) ? amount : 0;
  return currencyFormatter.format(value);
}

export function formatDate(isoDate) {
  if (!isoDate) return "";
  const [y, m, d] = isoDate.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function formatMonthYear(month, year) {
  return `${MONTH_NAMES[month - 1]} ${year}`;
}

export function todayISO() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/**
 * Human label for a bill reminder status, e.g. "Overdue by 3 days",
 * "Due Today", "Due in 7 days".
 */
export function formatReminderLabel(status, daysUntil) {
  if (status === "paid") return "Paid";
  if (status === "overdue") {
    const days = Math.abs(daysUntil);
    return `Overdue by ${days} day${days === 1 ? "" : "s"}`;
  }
  if (status === "due-today") return "Due Today";
  return `Due in ${daysUntil} day${daysUntil === 1 ? "" : "s"}`;
}
