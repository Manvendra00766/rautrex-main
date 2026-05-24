"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { 
  LayoutDashboard, 
  BarChart3, 
  PieChart, 
  ShieldCheck,
  Zap,
  Briefcase,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Database,
  Activity,
  Layers,
  AlertTriangle,
  DollarSign
} from "lucide-react";

const navGroups = [
  {
    title: "OVERVIEW",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Markets", href: "/dashboard/market", icon: Zap },
    ]
  },
  {
    title: "RESEARCH",
    items: [
      { label: "Stock Screener", href: "/dashboard/screener", icon: ShieldCheck },
      { label: "Compare", href: "/dashboard/compare", icon: Activity },
      { label: "Signals", href: "/dashboard/signals", icon: PieChart },
    ]
  },
  {
    title: "VALUATION & STRATEGY",
    items: [
      { label: "DCF Valuation", href: "/dashboard/dcf", icon: BarChart3 },
      { label: "Backtesting", href: "/dashboard/backtest", icon: RotateCcw },
      { label: "Monte Carlo", href: "/dashboard/monte-carlo", icon: Layers },
    ]
  },
  {
    title: "PORTFOLIO & RISK",
    items: [
      { label: "Portfolio", href: "/dashboard/portfolio", icon: Briefcase },
      { label: "Risk", href: "/dashboard/risk", icon: AlertTriangle },
      { label: "Options", href: "/dashboard/options", icon: Database },
    ]
  }
];

export function Sidebar() {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside className={cn(
      "hidden md:flex h-full bg-[var(--sidebar-bg)] border-r border-[var(--border)] flex-col flex-shrink-0 transition-all duration-300 ease-in-out relative group/sidebar",
      isCollapsed ? "w-[64px]" : "w-[240px]"
    )}>
      {/* COLLAPSE TOGGLE */}
      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-[var(--bg-surface)] border border-[var(--border)] flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[#8B6F47] transition-all z-10 opacity-0 group-hover/sidebar:opacity-100 shadow-sm"
      >
        {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* HEADER LOGO */}
      <div className={cn("p-4 border-b border-[var(--border)] flex items-center overflow-hidden", isCollapsed ? "justify-center" : "justify-between")}>
        <span className={cn("font-bold text-base tracking-tighter text-[var(--text-primary)] transition-all", isCollapsed && "scale-0 w-0 opacity-0")}>
          RAUTREX
        </span>
        <div className={cn("w-2 h-2 rounded-full bg-[#8B6F47] shrink-0", !isCollapsed && "hidden")} />
      </div>

      {/* NAVIGATION GROUPS */}
      <nav className="flex-1 p-2 space-y-4 overflow-y-auto overflow-x-hidden custom-scrollbar">
        {navGroups.map((group, groupIdx) => (
          <div key={group.title} className="flex flex-col">
            {/* Subtle divider and 8px gap before subsequent groups */}
            {groupIdx > 0 && (
              <div className="mb-2">
                <hr className="border-[var(--border)] opacity-60 my-1 mx-2" />
              </div>
            )}
            
            {/* Section label (hidden when collapsed) */}
            {!isCollapsed ? (
              <span className="px-3 pb-2 text-[10px] font-bold uppercase tracking-widest text-[#8C8278] select-none block">
                {group.title}
              </span>
            ) : null}

            {/* List of items */}
            <div className="space-y-[8px] flex flex-col">
              {group.items.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={isCollapsed ? item.label : ""}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-sm text-[11px] font-bold uppercase tracking-wider transition-all relative border-l-[3px]",
                      isActive 
                        ? "bg-[#EDE8DC] text-[var(--text-primary)] border-[#8B6F47]" 
                        : "text-[var(--text-secondary)] border-transparent hover:text-[var(--text-primary)] hover:bg-[#EDE8DC]/50"
                    )}
                  >
                    <item.icon size={16} className="shrink-0" />
                    {!isCollapsed && (
                      <span className="transition-opacity duration-200 truncate">
                        {item.label}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* FOOTER SYSTEM STATUS */}
      <div className={cn("p-4 border-t border-[var(--border)] flex items-center gap-2", isCollapsed ? "justify-center" : "px-4")}>
        <div className="w-2 h-2 rounded-full bg-[var(--positive)] animate-pulse shrink-0" />
        <span className={cn("text-[9px] font-bold text-[var(--text-muted)] uppercase tracking-widest transition-all", isCollapsed && "hidden")}>
          System Live
        </span>
      </div>
    </aside>
  );
}
