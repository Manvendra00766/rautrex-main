"use client";

import { Home, LineChart, Briefcase, TrendingUp, MoreHorizontal, Layers, Activity, AlertTriangle, DollarSign } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const mainNav = [
  { icon: Home, label: "Home", href: "/" },
  { icon: LineChart, label: "Markets", href: "/market" },
  { icon: TrendingUp, label: "Signals", href: "/signals" },
  { icon: Briefcase, label: "Portfolio", href: "/portfolio" },
];

const secondaryNav = [
  { icon: Layers, label: "Backtest", href: "/backtest" },
  { icon: Activity, label: "Monte Carlo", href: "/monte-carlo" },
  { icon: AlertTriangle, label: "Risk", href: "/risk" },
  { icon: DollarSign, label: "Options", href: "/options" },
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-[#0d0d14] border-t border-white/5 z-[100] flex items-center justify-around px-2">
      {mainNav.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link key={item.href} href={item.href} className="flex-1">
            <div className={cn(
              "flex flex-col items-center gap-1 transition-colors",
              isActive ? "text-accent" : "text-gray-500"
            )}>
              <item.icon size={20} className={isActive ? "cyan-glow" : ""} />
              <span className="text-[10px] font-bold uppercase tracking-tighter">{item.label}</span>
            </div>
          </Link>
        );
      })}

      <Popover>
        <PopoverTrigger asChild>
          <button className="flex-1 flex flex-col items-center gap-1 text-gray-500">
            <MoreHorizontal size={20} />
            <span className="text-[10px] font-bold uppercase tracking-tighter">More</span>
          </button>
        </PopoverTrigger>
        <PopoverContent side="top" className="w-[95vw] mb-4 bg-surface border-white/10 p-4 rounded-2xl grid grid-cols-2 gap-4">
          {secondaryNav.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link key={item.href} href={item.href}>
                <div className={cn(
                  "flex items-center gap-3 p-3 rounded-xl border",
                  isActive 
                    ? "bg-accent/10 border-accent/20 text-accent" 
                    : "bg-white/5 border-transparent text-gray-400"
                )}>
                  <item.icon size={18} />
                  <span className="text-xs font-bold uppercase tracking-widest">{item.label}</span>
                </div>
              </Link>
            );
          })}
        </PopoverContent>
      </Popover>
    </div>
  );
}
