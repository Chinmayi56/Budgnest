import React from "react";
import { Menu, Plus } from "lucide-react";

export default function Header({ title, subtitle, onMenuClick, onAddTransaction }) {
  return (
    <header className="sticky top-0 z-20 bg-paper/95 backdrop-blur border-b border-border">
      <div className="flex items-center justify-between h-16 px-4 sm:px-6">
        <div className="flex items-center gap-3 min-w-0">
          <button
            className="lg:hidden text-ink/70 hover:text-ink p-1.5 -ml-1.5"
            onClick={onMenuClick}
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>
          <div className="min-w-0">
            <h1 className="text-lg sm:text-xl font-display font-semibold text-ink truncate">
              {title}
            </h1>
            {subtitle && (
              <p className="text-xs text-ink/50 truncate hidden sm:block">{subtitle}</p>
            )}
          </div>
        </div>

        {onAddTransaction && (
          <button
            onClick={onAddTransaction}
            className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-3.5 py-2 rounded-lg shadow-sm transition-colors shrink-0"
          >
            <Plus size={16} />
            <span className="hidden sm:inline">Add Transaction</span>
            <span className="sm:hidden">Add</span>
          </button>
        )}
      </div>
    </header>
  );
}
