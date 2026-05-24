"use client";

import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";

interface MetricCardProps {
  label?: string;
  title?: string;
  value: string;
  change?: string;
  trend?: "up" | "down";
  subtext?: string;
  loading?: boolean;
  accent?: boolean; // For the black top-border accent
  large?: boolean;  // For the large NAV card styling
}

export function MetricCard({
  label,
  title,
  value,
  change,
  trend,
  subtext,
  loading = false,
  accent = false,
  large = false,
}: MetricCardProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-5 animate-pulse">
        <div className="h-3 w-20 bg-[var(--bg-elevated)] rounded mb-4" />
        <div className="h-8 w-32 bg-[var(--bg-elevated)] rounded" />
      </div>
    );
  }

  const displayTitle = label || title || "";
  const displayChange = change ? (change.startsWith("+") || change.startsWith("-") ? change : (trend === "up" ? `+${change}` : change)) : "";

  return (
    <div className={cn(
      "bg-[var(--bg-surface)] border border-[var(--border)] rounded-sm p-4 flex flex-col justify-between transition-all duration-200 hover:border-[var(--border-strong)]",
      accent && "border-t-[3px] border-t-[var(--accent)]"
    )}>
      <div>
        <div className="flex justify-between items-start mb-2">
          <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-[0.15em]">
            {displayTitle}
          </span>
          {trend && change && (
            <div
              className={cn(
                "px-2 py-0.5 rounded text-[10px] font-bold font-mono border",
                trend === "up" 
                  ? "bg-positive/10 text-positive border-positive/20" 
                  : "bg-negative/10 text-negative border-negative/20"
              )}
            >
              {displayChange}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <span className={cn(
            "font-mono font-bold tracking-tighter text-[var(--text-primary)]",
            large ? "text-[40px] leading-tight" : "text-2xl"
          )}>
            {value}
          </span>
        </div>
      </div>
      
      {subtext && (
        <span className="text-[11px] text-[var(--text-muted)] mt-3 font-medium">
          {subtext}
        </span>
      )}
    </div>
  );
}
