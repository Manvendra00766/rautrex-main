"use client";

import React, { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return (
    <div className="w-14 h-7 bg-[var(--toggle-bg)] 
    border border-[var(--toggle-border)] rounded-full animate-pulse" />
  );

  const isDark = theme === "dark";

  return (
    <div className="relative group">
      <button
        aria-label={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
        onClick={() => setTheme(isDark ? "light" : "dark")}
        className="relative w-14 h-7 
          bg-[var(--toggle-bg)] 
          border border-[var(--toggle-border)] 
          rounded-full flex items-center px-1 
          hover:border-[var(--accent-primary)] 
          transition-all duration-200"
      >
        <div className="absolute flex items-center 
          justify-between w-full px-2">
          <Moon 
            size={11} 
            className={`transition-opacity duration-200
              text-[var(--text-muted)]
              ${isDark ? "opacity-100" : "opacity-30"}`} 
          />
          <Sun 
            size={11} 
            className={`transition-opacity duration-200
              text-[var(--accent-amber)]
              ${isDark ? "opacity-30" : "opacity-100"}`} 
          />
        </div>
        <div className={`
          z-10 w-5 h-5 rounded-full 
          bg-[var(--bg-surface)] 
          border border-[var(--border-strong)] 
          shadow-sm
          transition-transform duration-300 
          ease-[cubic-bezier(0.4,0,0.2,1)]
          ${isDark ? "translate-x-0" : "translate-x-7"}
        `} />
      </button>
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 
        mb-2 px-2 py-1 rounded
        bg-[var(--bg-elevated)] 
        border border-[var(--border)]
        text-[var(--text-primary)] 
        text-xs font-medium whitespace-nowrap
        opacity-0 group-hover:opacity-100 
        transition-opacity duration-150 pointer-events-none">
        {isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
      </div>
    </div>
  );
}
