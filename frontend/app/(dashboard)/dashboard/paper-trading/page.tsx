'use client';

import React, { Suspense } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardHeader, CardContent } from '@/components/ui/card';

const PaperTradingDashboard = dynamic(
  () => import('@/components/paper-trading/PaperTradingDashboard'),
  { ssr: false }
);

function SkeletonStats() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i} className="bg-elevated/50 border-border animate-pulse">
          <CardHeader className="h-12" />
          <CardContent className="h-16" />
        </Card>
      ))}
    </div>
  );
}

function SkeletonMain() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-8 space-y-6">
        <Card className="bg-elevated/50 border-border h-64 animate-pulse" />
        <Card className="bg-elevated/50 border-border h-64 animate-pulse" />
      </div>
      <div className="lg:col-span-4">
        <Card className="bg-elevated/50 border-border h-[500px] animate-pulse" />
      </div>
    </div>
  );
}

export default function PaperTradingPage() {
  return (
    <div className="space-y-8 p-6 lg:p-8 bg-background min-h-screen">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Paper Trading</h1>
        <p className="text-muted">
          Practice your trading strategies with <span className="text-accent font-semibold">₹10,00,000</span> virtual cash.
        </p>
      </div>

      <Suspense fallback={
        <div className="space-y-6">
          <SkeletonStats />
          <SkeletonMain />
        </div>
      }>
        <PaperTradingDashboard />
      </Suspense>
    </div>
  );
}
