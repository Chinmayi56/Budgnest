import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { clearSession } from "../utils/api.js";
import {
  LayoutDashboard,
  ArrowLeftRight,
  PieChart,
  LogOut,
  Wallet,
  X,
  Receipt,
  HandCoins,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { to: "/bills", label: "Bills & Payments", icon: Receipt },
  { to: "/estimation", label: "Estimation", icon: HandCoins },
  { to: "/reports", label: "Reports", icon: PieChart },
];

export default function Sidebar({ isOpen, onClose }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    // Must clear the stored token/user before navigating away — leaving
    // it in localStorage would let the next person to open the app in
    // this browser inherit this account's signed-in session and data.
    clearSession();
    navigate("/login");
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-ink/40 z-30 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 left-0 z-40 h-full w-64 bg-brand-700 text-white flex flex-col
        transform transition-transform duration-200 ease-out
        ${isOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0 lg:static lg:z-auto`}
      >
        <div className="flex items-center justify-between px-6 h-16 border-b border-white/10">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-white/10 flex items-center justify-center">
              <Wallet size={18} />
            </div>
            <span className="font-display font-semibold text-lg tracking-tight">
              BudgetNest
            </span>
          </div>
          <button
            className="lg:hidden text-white/70 hover:text-white"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 px-3 py-6 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-white text-brand-700"
                    : "text-white/75 hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-white/10">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-white/75 hover:bg-white/10 hover:text-white transition-colors"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>
    </>
  );
}
