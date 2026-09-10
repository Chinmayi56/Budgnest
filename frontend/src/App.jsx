import React from "react";
import { useLocation } from "react-router-dom";
import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./layouts/AppLayout.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Transactions from "./pages/Transactions.jsx";
import BillsPayments from "./pages/BillsPayments.jsx";
import Estimation from "./pages/Estimation.jsx";
import Reports from "./pages/Reports.jsx";

function Protected({ children }) { return localStorage.getItem("budgetnest_token") ? children : <Navigate to="/login" replace />; }

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />

      <Route element={<Protected><AppLayout /></Protected>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/bills" element={<BillsPayments />} />
        <Route path="/estimation" element={<Estimation />} />
        <Route path="/money-given" element={<Navigate to="/estimation" replace />} />
        <Route path="/reports" element={<Reports />} />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
