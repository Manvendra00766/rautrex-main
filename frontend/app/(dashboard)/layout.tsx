import React from "react";
import DashboardClientWrapper from "@/components/layout/DashboardClientWrapper";
import { SandboxProvider } from "@/lib/sandboxContext";
import { SandboxBanner } from "@/components/layout/SandboxBanner";

export const dynamic = 'force-dynamic';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SandboxProvider>
      <div className="flex flex-col h-screen overflow-hidden">
        <SandboxBanner />
        <div className="flex-1 flex overflow-hidden relative">
          <DashboardClientWrapper>{children}</DashboardClientWrapper>
        </div>
      </div>
    </SandboxProvider>
  );
}
