import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { formatCurrency, MONTH_NAMES } from "../../utils/formatters.js";

export default function MonthlyTrendChart({ monthlyBreakdown }) {
  const data = monthlyBreakdown.map((m) => ({
    name: MONTH_NAMES[m.month - 1].slice(0, 3),
    Income: m.income,
    Expenses: m.expenses,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#E2E8E4" />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#10231D99" }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fontSize: 11, fill: "#10231D99" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `₹${v / 1000}k`}
        />
        <Tooltip formatter={(value) => formatCurrency(value)} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="Income" stroke="#1B8A5A" strokeWidth={2.5} dot={false} />
        <Line type="monotone" dataKey="Expenses" stroke="#C24A3B" strokeWidth={2.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
