import React from "react";
import { cn } from "@/lib/utils";

interface DataTableProps extends React.TableHTMLAttributes<HTMLTableElement> {}

export function DataTable({ className, children, ...props }: DataTableProps) {
  return (
    <div className="w-full overflow-x-auto custom-scrollbar rounded-lg border border-border">
      <table className={cn("w-full text-left border-collapse font-mono text-[14px]", className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export function TableHead({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={cn("px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-widest border-b border-border bg-card", className)} {...props} />;
}

export function TableRow({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("border-b border-border hover:bg-card/50 transition-colors", className)} {...props} />;
}

export function TableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-3 text-text-primary", className)} {...props} />;
}
