"use client";

import React from "react";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { Search, Globe, Activity } from "lucide-react";

export function Navbar() {
  return (
    <header className="h-14 
      bg-[var(--bg-surface)] 
      border-b border-[var(--border)]
      flex items-center justify-between 
      px-4 flex-shrink-0 z-50">
      
      <div className="flex items-center gap-8 flex-1">
        <span className="font-bold text-[var(--text-primary)] tracking-tighter hidden md:block">
          RAUTREX
        </span>

        {/* SEARCH BAR */}
        <div className="relative max-w-md w-full group hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] group-focus-within:text-[var(--accent-primary)] transition-colors" size={14} />
          <input 
            type="text" 
            placeholder="Search symbols, models or analytics..." 
            className="w-full bg-[var(--bg-base)] border border-[var(--border)] rounded-lg pl-9 pr-4 py-1.5 text-xs font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]/20 transition-all"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 hidden lg:flex items-center gap-1 px-1.5 py-0.5 rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] text-[9px] font-bold text-[var(--text-muted)]">
            <span className="opacity-70">⌘</span>K
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {/* MARKET STATUS PILLS */}
        <div className="hidden lg:flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[var(--bg-elevated)] border border-[var(--border)]">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--positive)]" />
            <span className="text-[9px] font-bold text-[var(--text-primary)] uppercase tracking-wider">NYSE: OPEN</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[var(--bg-elevated)] border border-[var(--border)]">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] opacity-50" />
            <span className="text-[9px] font-bold text-[var(--text-muted)] uppercase tracking-wider">LSE: CLOSED</span>
          </div>
        </div>

        <div className="flex items-center gap-4 border-l border-[var(--border)] pl-6">
          <button className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
            <Activity size={18} />
          </button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
