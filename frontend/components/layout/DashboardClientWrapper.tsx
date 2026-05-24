"use client";

import React from "react";
import Sidebar from "@/components/sidebar";
import Topbar from "@/components/topbar";
import BottomNav from "@/components/BottomNav";
import { useHasMounted } from "@/lib/hooks";

export default function DashboardClientWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const hasMounted = useHasMounted();

  if (!hasMounted) {
    return (
      <div className="flex h-screen overflow-hidden bg-background">
        <div className="hidden md:flex h-full w-[260px] bg-surface border-r border-white/5 flex-col" />
        <div className="flex-1 flex flex-col min-w-0 h-full relative">
          <header className="h-16 border-b border-white/5 flex items-center px-6" />
          <main className="flex-1 p-4 md:p-6 bg-background" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        <Topbar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-6 pb-32 md:pb-12 custom-scrollbar">
          {children}
        </main>
        <BottomNav />
      </div>
    </div>
  );
}
