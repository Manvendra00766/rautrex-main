import React from "react";
import Sidebar from "@/components/sidebar";
import Topbar from "@/components/topbar";
import BottomNav from "@/components/BottomNav";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Sidebar />
      <div className="flex-1 flex flex-col h-full relative overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-background pb-24 md:pb-6">
          {children}
        </main>
        <BottomNav />
      </div>
    </>
  );
}
