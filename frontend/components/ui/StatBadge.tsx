import React from "react";
import { cn } from "@/lib/utils";

interface StatBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "positive" | "negative" | "warning";
}

export function StatBadge({ className, variant = "default", children, ...props }: StatBadgeProps) {
  const variants = {
    default: "bg-muted text-text-secondary border-border",
    positive: "bg-positive/10 text-positive border-positive/20",
    negative: "bg-negative/10 text-negative border-negative/20",
    warning: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  };

  return (
    <div 
      className={cn(
        "px-2 py-0.5 rounded text-xs font-bold font-mono border inline-flex items-center",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
