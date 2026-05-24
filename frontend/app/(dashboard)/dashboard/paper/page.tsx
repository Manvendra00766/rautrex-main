'use client';

import dynamic from 'next/dynamic';
import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

const PaperTradingDashboard = dynamic(
  () => import('@/components/paper/PaperTradingDashboard'),
  { ssr: false }
);

export default function PaperTradingPage() {
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex flex-col gap-2 px-4">
        <h1 className="text-3xl font-bold tracking-tight">Paper Trading</h1>
        <p className="text-muted-foreground">
          Simulate real-market trades with ₹10,00,000 virtual cash. No real money involved.
        </p>
      </div>

      <Suspense fallback={
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      }>
        <PaperTradingDashboard />
      </Suspense>
    </div>
  );
}
