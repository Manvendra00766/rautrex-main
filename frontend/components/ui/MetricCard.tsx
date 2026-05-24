import React from "react";
import { cn } from "@/lib/utils";
import { StatBadge } from "./StatBadge";

interface MetricCardProps {
  title?: string;
  label?: string;
  value: string;
  change?: string;
  trend?: "up" | "down" | "neutral";
  subtext?: string;
  icon?: React.ReactNode;
  className?: string;
  accent?: boolean;
  large?: boolean;
}

export function MetricCard({ title, label, value, change, trend, subtext, icon, className }: MetricCardProps) {
  const displayTitle = title || label || "";
  const displayChange = change ? (change.startsWith("+") || change.startsWith("-") ? change : (trend === "up" ? `+${change}` : change)) : "";

  return (
    <div 
      className={cn(
        "bg-surface border border-border shadow-sm rounded-lg p-5 flex flex-col relative overflow-hidden",
        className
      )}
    >
      {icon && (
        <div className="absolute top-5 right-5 text-accent opacity-20">
          {icon}
        </div>
      )}
      
      <p className="text-[12px] font-bold text-text-muted uppercase tracking-widest mb-2">{displayTitle}</p>
      
      <div className="flex items-baseline gap-3 mb-1">
        <div className="text-[28px] lg:text-[36px] font-black text-text-primary tracking-tight font-mono">
          {value}
        </div>
        {change && (
          <StatBadge variant={trend === "up" ? "positive" : trend === "down" ? "negative" : "default"}>
            {displayChange}
          </StatBadge>
        )}
      </div>
      
      {subtext && (
        <p className="text-[14px] text-text-secondary font-medium">
          {subtext}
        </p>
      )}
    </div>
  );
}
