"use client";

import { Search, User, LogOut, Loader2, Menu } from "lucide-react";
import { useState, useEffect } from "react";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { createClient } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import NotificationBell from "./NotificationBell";
import { useMarketStore } from "@/lib/market-store";
import { cn } from "@/lib/utils";

export default function Topbar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const { user } = useAuthStore();
  const { setActiveTicker } = useMarketStore();
  const supabase = createClient();
  const router = useRouter();

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
    <header className="h-16 glass-panel flex items-center justify-between px-4 md:px-6 z-[100] sticky top-0">
      {/* Mobile Search - Smaller or just Icon */}
      <div className="relative flex-1 max-w-xs md:max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
        <input 
          type="text" 
          placeholder="Search tickers..." 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-surface/50 border border-white/5 rounded-full py-1.5 pl-9 pr-4 text-xs md:text-sm focus:outline-none focus:border-accent text-white font-mono placeholder:font-sans transition-all"
        />
        {results.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-surface border border-white/10 rounded-xl overflow-hidden shadow-2xl z-[110]">
            {results.map((r: any) => (
              <div 
                key={r.ticker} 
                className="p-3 hover:bg-white/5 cursor-pointer flex justify-between items-center"
                onClick={() => handleSelect(r.ticker)}
              >
                <span className="font-mono font-bold text-accent text-xs">{r.ticker}</span>
                <span className="text-[10px] text-gray-500 truncate ml-4">{r.name}</span>
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
              {user ? getInitials(user) : <User size={14} />}
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-56 p-2 bg-surface border-white/10 text-white shadow-2xl rounded-2xl" align="end">
            <div className="px-2 py-2 mb-2 border-b border-white/5">
              <p className="text-xs font-bold truncate uppercase tracking-widest">{user?.user_metadata?.full_name || "Quant Trader"}</p>
              <p className="text-[10px] text-gray-500 truncate font-mono">{user?.email}</p>
            </div>
            <Button 
              variant="ghost" 
              className="w-full justify-start text-[10px] font-bold uppercase tracking-widest text-red-400 hover:text-red-300 hover:bg-red-500/10 h-10 rounded-xl"
              onClick={handleLogout}
            >
              <LogOut size={14} className="mr-2" />
              Sign Out
            </Button>
          </PopoverContent>
        </Popover>
      </div>
    </header>
  );
}
