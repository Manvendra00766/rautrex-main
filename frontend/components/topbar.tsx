"use client";

import { 
  Search, 
  User, 
  LogOut, 
  Loader2, 
  Menu, 
  X, 
  LayoutDashboard, 
  BarChart3, 
  PieChart, 
  ShieldCheck, 
  Zap, 
  Briefcase, 
  RotateCcw, 
  Layers, 
  AlertTriangle, 
  Database, 
  Activity 
} from "lucide-react";
import { useState, useEffect } from "react";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { createClient } from "@/lib/supabase";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import NotificationBell from "./NotificationBell";
import { useMarketStore } from "@/lib/market-store";
import { cn } from "@/lib/utils";
import { useHasMounted } from "@/lib/hooks";

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

export default function Topbar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const { user } = useAuthStore();
  const { setActiveTicker } = useMarketStore();
  const supabase = createClient();
  const router = useRouter();
  const pathname = usePathname();
  const hasMounted = useHasMounted();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const handleSelect = (ticker: string) => {
    setActiveTicker(ticker);
    setQuery("");
    setResults([]);
  };

  useEffect(() => {
    if (query.length > 1) {
      const fetchResults = async () => {
        try {
          const res = await api.get(`/stocks/search?q=${query}`);
          setResults(res.data.results);
        } catch (error) {
          console.error("Search failed", error);
        }
      };
      const debounce = setTimeout(fetchResults, 300);
      return () => clearTimeout(debounce);
    } else {
      setResults([]);
    }
  }, [query]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  };

  const getInitials = (user: any) => {
    const fullName = user?.user_metadata?.full_name || user?.email || "User";
    return fullName.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);
  };

  return (
    <>
      <header className="h-16 glass-panel flex items-center justify-between px-4 md:px-6 z-[100] sticky top-0 gap-3">
        {/* Mobile Hamburger Icon */}
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="md:hidden p-1 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors shrink-0"
        >
          <Menu size={22} />
        </button>

        {/* Mobile Search - Smaller or just Icon */}
        <div className="relative flex-1 max-w-xs md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <input 
            type="text" 
            placeholder="Search tickers..." 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-white border border-black/20 rounded-full py-1.5 pl-9 pr-4 text-xs md:text-sm focus:outline-none focus:border-accent text-black font-mono placeholder:font-sans transition-all"
          />
          {results.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-surface border border-[var(--border)] rounded-xl overflow-hidden shadow-2xl z-[110]">
              {results.map((r: any) => (
                <div 
                  key={r.ticker} 
                  className="p-3 hover:bg-[var(--bg-secondary)] cursor-pointer flex justify-between items-center"
                  onClick={() => handleSelect(r.ticker)}
                >
                  <span className="font-mono font-bold text-accent text-xs">{r.ticker}</span>
                  <span className="text-xs text-gray-500 truncate ml-4">{r.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 md:gap-4 ml-4">
          <NotificationBell />
          
          <Popover>
            <PopoverTrigger asChild>
              <button className="w-8 h-8 rounded-full bg-accent-secondary/20 border border-accent-secondary/30 flex items-center justify-center text-accent-secondary font-black text-xs hover:opacity-80 transition-opacity">
                {hasMounted && user ? getInitials(user) : <User size={14} />}
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-56 p-2 bg-surface border-[var(--border)] text-[var(--text-primary)] shadow-2xl rounded-2xl" align="end">
              <div className="px-2 py-2 mb-2 border-b border-[var(--border)]">
                <p className="text-xs font-bold truncate uppercase tracking-widest">
                  {hasMounted ? (user?.user_metadata?.full_name || "Quant Trader") : "Loading..."}
                </p>
                <p className="text-xs text-gray-500 truncate font-mono">
                  {hasMounted ? user?.email : "..."}
                </p>
              </div>
              <Button 
                variant="ghost" 
                className="w-full justify-start text-xs font-bold uppercase tracking-widest text-[var(--negative)] hover:bg-[var(--bg-secondary)] hover:text-[var(--negative)] h-10 rounded-xl"
                onClick={handleLogout}
              >
                <LogOut size={14} className="mr-2" />
                Sign Out
              </Button>
            </PopoverContent>
          </Popover>
        </div>
      </header>

      {/* Mobile slide-over drawer overlay */}
      <AnimatePresence>
        {isDrawerOpen && (
          <>
            {/* Backdrop */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsDrawerOpen(false)}
              className="fixed inset-0 bg-black z-[150] md:hidden"
            />

            {/* Slide-over panel */}
            <motion.div 
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 220 }}
              className="fixed inset-y-0 left-0 w-[280px] bg-[#0A0E1A] border-r border-[#1E2A3A] z-[200] md:hidden flex flex-col shadow-2xl overflow-hidden"
            >
              {/* Drawer Header */}
              <div className="p-4 border-b border-[#1E2A3A] flex items-center justify-between">
                <span className="font-bold text-xs tracking-tighter text-white">
                  RAUTREX TERMINAL
                </span>
                <button 
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Drawer Navigation List */}
              <nav className="flex-1 p-3 space-y-4 overflow-y-auto custom-scrollbar">
                {navGroups.map((group, groupIdx) => (
                  <div key={group.title} className="flex flex-col">
                    {groupIdx > 0 && (
                      <div className="mb-2">
                        <hr className="border-[#1E2A3A] opacity-60 my-1 mx-2" />
                      </div>
                    )}
                    
                    <span className="px-3 pb-2 text-xs font-bold uppercase tracking-widest text-[#8C8278] select-none block">
                      {group.title}
                    </span>

                    <div className="space-y-[6px] flex flex-col">
                      {group.items.map((item) => {
                        const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                        return (
                          <Link
                            key={item.href}
                            href={item.href}
                            onClick={() => setIsDrawerOpen(false)}
                            className={cn(
                              "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all relative border-l-[3px]",
                              isActive 
                                ? "bg-[#EDE8DC] text-[#0A0E1A] border-[#8B6F47]" 
                                : "text-gray-400 border-transparent hover:text-white hover:bg-white/5"
                            )}
                          >
                            <item.icon size={15} className="shrink-0" />
                            <span className="truncate">{item.label}</span>
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </nav>

              {/* Status Footer */}
              <div className="p-4 border-t border-[#1E2A3A] flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                <span className="text-[8px] font-bold text-gray-500 uppercase tracking-widest">
                  System Online (Live)
                </span>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
