"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { 
  LayoutDashboard, 
  Briefcase, 
  ShieldCheck, 
  PieChart, 
  BarChart3 
} from "lucide-react";

const mainNav = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: Briefcase, label: "Portfolio", href: "/dashboard/portfolio" },
  { icon: ShieldCheck, label: "Screener", href: "/dashboard/screener" },
  { icon: PieChart, label: "Signals", href: "/dashboard/signals" },
  { icon: BarChart3, label: "DCF Val", href: "/dashboard/dcf" },
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-[#EDE8DC] border-t border-[#D4CEC4] z-[100] flex items-center justify-around px-2 shadow-lg">
      {mainNav.map((item) => {
        const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <Link key={item.href} href={item.href} className="flex-1">
            <div className={cn(
              "flex flex-col items-center gap-1 transition-colors py-1 cursor-pointer",
              isActive ? "text-[#8B6F47]" : "text-[#8C8278] hover:text-[var(--text-primary)]"
            )}>
              <item.icon size={18} />
              <span className="text-[9px] font-bold uppercase tracking-tighter truncate">
                {item.label}
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
