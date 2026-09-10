import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { formatCurrency } from "../../utils/formatters.js";

export default function IncomeExpenseBarChart({ income, expenses }) {
  const data = [{ name: "This Period", Income: income, Expenses: expenses }];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} barGap={12} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#E2E8E4" />
        <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#10231D99" }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fontSize: 11, fill: "#10231D99" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `₹${v / 1000}k`}
        />
        <Tooltip formatter={(value) => formatCurrency(value)} />
        <Bar dataKey="Income" fill="#1B8A5A" radius={[6, 6, 0, 0]} maxBarSize={60} />
        <Bar dataKey="Expenses" fill="#C24A3B" radius={[6, 6, 0, 0]} maxBarSize={60} />
      </BarChart>
    </ResponsiveContainer>
  );
}
