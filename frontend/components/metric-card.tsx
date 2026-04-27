"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  trend?: string;
  trendColor?: string;
  className?: string;
  valueClassName?: string;
}

export default function MetricCard({ title, value, icon, trend, trendColor, className, valueClassName }: MetricCardProps) {
  return (
    <div 
      className={cn(
        "glass-panel p-5 rounded-2xl flex flex-col gap-1 relative overflow-hidden group border border-white/[0.02] bg-[#0d0d14] hover:bg-[#11111a] transition-colors",
        className
      )}
    >
      {icon && (
        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-30 transition-opacity">
          {icon}
        </div>
      )}
      
      <p className="text-[10px] md:text-xs font-bold text-gray-500 uppercase tracking-widest">{title}</p>
      
      <div className="flex items-baseline gap-1 mt-1">
        <div className={cn("text-2xl md:text-3xl font-black text-white tracking-tight font-mono", valueClassName)}>
          {value}
        </div>
      </div>
      
      {trend && (
        <p className={cn("text-[10px] md:text-xs font-mono font-bold mt-2", trendColor || "text-gray-400")}>
          {trend}
        </p>
      )}
    </div>
  );
}
