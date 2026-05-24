"use client";

import { cn } from "@/lib/utils";
import React from "react";

interface Column {
  header: string;
  accessor: string;
  className?: string;
  render?: (value: any, row: any) => React.ReactNode;
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  onRowClick?: (row: any) => void;
  loading?: boolean;
}

export function DataTable({ columns, data, onRowClick, loading }: DataTableProps) {
  return (
    <div className="w-full overflow-x-auto custom-scrollbar border border-[var(--border)] rounded-xl bg-[var(--bg-surface)]">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-[var(--border)] bg-[var(--bg-elevated)]/30">
            {columns.map((col, idx) => (
              <th
                key={idx}
                className={cn(
                  "px-4 py-3 text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest",
                  col.className
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {loading ? (
            Array.from({ length: 5 }).map((_, idx) => (
              <tr key={idx} className="animate-pulse">
                {columns.map((_, cIdx) => (
                  <td key={cIdx} className="px-4 py-4">
                    <div className="h-3 bg-[var(--bg-elevated)] rounded w-3/4" />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-12 text-center text-xs text-[var(--text-muted)] italic"
              >
                No data available
              </td>
            </tr>
          ) : (
            data.map((row, rIdx) => (
              <tr
                key={rIdx}
                onClick={() => onRowClick?.(row)}
                className={cn(
                  "transition-colors group",
                  onRowClick ? "cursor-pointer hover:bg-[var(--bg-elevated)]" : "hover:bg-[var(--bg-elevated)]/50"
                )}
              >
                {columns.map((col, cIdx) => (
                  <td
                    key={cIdx}
                    className={cn(
                      "px-4 py-3 text-xs font-medium text-[var(--text-primary)]",
                      col.className
                    )}
                  >
                    {col.render ? col.render(row[col.accessor], row) : row[col.accessor]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
