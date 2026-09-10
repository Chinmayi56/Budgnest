import React from "react";
import { FileText, FileSpreadsheet } from "lucide-react";
import { exportTransactionsToPDF, exportTransactionsToExcel } from "../utils/exporters.js";

/**
 * A small pair of "Export PDF" / "Export Excel" buttons. Pass the
 * transactions to export plus optional title/subtitle/summary/filename
 * options (see utils/exporters.js). Disabled automatically when there's
 * nothing to export.
 */
export default function ExportButtons({ transactions, title, subtitle, summary, filenameBase = "budgetnest-export" }) {
  const disabled = !transactions || transactions.length === 0;

  const handlePdf = () => {
    exportTransactionsToPDF(transactions, {
      title,
      subtitle,
      summary,
      filename: `${filenameBase}.pdf`,
    });
  };

  const handleExcel = () => {
    exportTransactionsToExcel(transactions, {
      summary,
      filename: `${filenameBase}.xlsx`,
    });
  };

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handlePdf}
        disabled={disabled}
        className="flex items-center gap-1.5 border border-border bg-white hover:bg-paper disabled:opacity-50 disabled:cursor-not-allowed text-ink/70 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors"
        title={disabled ? "No transactions to export" : "Export as PDF"}
      >
        <FileText size={15} />
        <span className="hidden sm:inline">PDF</span>
      </button>
      <button
        type="button"
        onClick={handleExcel}
        disabled={disabled}
        className="flex items-center gap-1.5 border border-border bg-white hover:bg-paper disabled:opacity-50 disabled:cursor-not-allowed text-ink/70 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors"
        title={disabled ? "No transactions to export" : "Export as Excel"}
      >
        <FileSpreadsheet size={15} />
        <span className="hidden sm:inline">Excel</span>
      </button>
    </div>
  );
}
