"use client";

import { useState, useEffect } from "react";
import { 
  Home, 
  LineChart, 
  Briefcase, 
  Layers, 
  Activity, 
  TrendingUp, 
  AlertTriangle, 
  DollarSign, 
  ChevronLeft, 
  ChevronRight,
  MoreHorizontal
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useIsTablet, useIsMobile } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export const navItems = [
  { icon: Home, label: "Dashboard", href: "/dashboard" },
  { icon: LineChart, label: "Markets", href: "/market" },
  { icon: Briefcase, label: "Portfolio", href: "/portfolio" },
  { icon: Layers, label: "Backtest", href: "/backtest" },
  { icon: Activity, label: "Compare", href: "/compare" },
  { icon: Activity, label: "Monte Carlo", href: "/monte-carlo" },
  { icon: TrendingUp, label: "Signals", href: "/signals" },
  { icon: AlertTriangle, label: "Risk", href: "/risk" },
  { icon: DollarSign, label: "Options", href: "/options" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const isTablet = useIsTablet();
  const isMobile = useIsMobile();

  // Auto-collapse on tablet
  useEffect(() => {
    if (isTablet) setCollapsed(true);
    else if (!isMobile) setCollapsed(false);
  }, [isTablet, isMobile]);

  if (isMobile) return null;

  return (
    <motion.aside 
      initial={false}
      animate={{ width: collapsed ? 80 : 260 }}
      className={cn(
        "h-full bg-surface border-r border-white/5 flex flex-col relative z-20 transition-all duration-300",
        "hidden md:flex"
      )}
    >
      <div className="h-16 flex items-center justify-center border-b border-white/5 overflow-hidden">
        <h1 className="font-bold text-xl tracking-tighter text-white flex items-center gap-2">
          <div className="w-6 h-6 bg-accent rounded-sm shrink-0" />
          {!collapsed && <span className="text-accent">RAUTREX</span>}
        </h1>
      </div>

      <nav className="flex-1 py-6 flex flex-col gap-2 px-3 overflow-y-auto custom-scrollbar">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          
          const NavLink = (
            <Link key={item.href} href={item.href} className="block">
              <div className={cn(
                "flex items-center gap-4 px-3 py-3 rounded-xl cursor-pointer transition-all group",
                isActive 
                  ? "bg-accent/10 text-accent border border-accent/20" 
                  : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
              )}>
                <item.icon size={20} className={cn("shrink-0", isActive && "cyan-glow")} />
                {!collapsed && (
                  <motion.span 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="font-bold text-xs uppercase tracking-widest"
                  >
                    {item.label}
                  </motion.span>
                )}
              </div>
            </Link>
          );

          if (collapsed) {
            return (
              <Popover key={item.href}>
                <PopoverTrigger asChild>
                  {NavLink}
                </PopoverTrigger>
                <PopoverContent side="right" className="bg-surface border-white/10 text-white font-bold text-[10px] uppercase tracking-widest p-2 px-3 w-fit ml-2">
                  {item.label}
                </PopoverContent>
              </Popover>
            );
          }

          return NavLink;
        })}
      </nav>

      {!isTablet && (
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3 top-20 bg-surface border border-white/10 rounded-full p-1 text-gray-400 hover:text-white z-30 transition-transform hover:scale-110"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      )}

      <div className="p-4 border-t border-white/5 flex flex-col gap-4">
         {!collapsed && (
            <div className="bg-accent/5 border border-accent/10 rounded-xl p-3">
               <p className="text-[10px] font-bold text-accent uppercase tracking-tighter mb-1">System Status</p>
               <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-[10px] text-gray-400 font-mono">ALL SYSTEMS NOMINAL</span>
               </div>
            </div>
         )}
      </div>
    </motion.aside>
  );
}
