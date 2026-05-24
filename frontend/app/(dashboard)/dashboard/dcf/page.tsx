'use client';

import { Suspense } from 'react';
import dynamic from 'next/dynamic';

const DCFCalculator = dynamic(() => import('@/components/dcf/DCFCalculator'), {
  ssr: false,
});

export default function DCFPage() {
  return (
    <div className="container mx-auto py-8 px-4 md:px-6 pb-20">
      <Suspense fallback={<DCFSkeleton />}>
        <DCFCalculator />
      </Suspense>
    </div>
  );
}

function DCFSkeleton() {
  return (
    <div className="space-y-8 animate-pulse">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="h-[600px] bg-elevated rounded-2xl w-full" />
        <div className="space-y-8">
          <div className="h-[300px] bg-elevated rounded-2xl w-full" />
          <div className="h-[250px] bg-elevated rounded-2xl w-full" />
        </div>
      </div>
      <div className="h-10 bg-elevated rounded-lg w-48" />
    </div>
  );
}
