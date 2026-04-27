"use client";

import React from 'react';
import { cn } from '@/lib/utils';

interface ChartSkeletonProps {
  type?: 'line' | 'bar' | 'pie';
  className?: string;
}

export const ChartSkeleton: React.FC<ChartSkeletonProps> = ({ type = 'line', className }) => {
  return (
    <div className={cn(
      "w-full h-full flex flex-col items-center justify-center bg-[#0d0d14] rounded-2xl p-6 relative overflow-hidden",
      className
    )}>
      {/* Pulse Animation Overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" 
           style={{ backgroundSize: '200% 100%' }} />

      {type === 'line' && (
        <div className="w-full h-full flex flex-col justify-around py-10 opacity-40">
          <div className="h-[2px] w-3/4 bg-border-tertiary animate-pulse self-start" />
          <div className="h-[2px] w-1/2 bg-border-tertiary animate-pulse self-center" />
          <div className="h-[2px] w-2/3 bg-border-tertiary animate-pulse self-end" />
        </div>
      )}

      {type === 'bar' && (
        <div className="w-full h-full flex items-end justify-around pb-10 gap-4 opacity-40">
          <div className="w-8 bg-border-tertiary animate-pulse h-1/3" />
          <div className="w-8 bg-border-tertiary animate-pulse h-2/3" />
          <div className="w-8 bg-border-tertiary animate-pulse h-1/2" />
          <div className="w-8 bg-border-tertiary animate-pulse h-3/4" />
          <div className="w-8 bg-border-tertiary animate-pulse h-2/5" />
        </div>
      )}

      {type === 'pie' && (
        <div className="relative w-48 h-48 rounded-full border-[20px] border-border-tertiary animate-pulse opacity-40">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full rounded-full border-[20px] border-transparent border-t-border-tertiary rotate-45" />
        </div>
      )}
      
      <style jsx>{`
        @keyframes shimmer {
          100% {
            transform: translateX(100%);
          }
        }
        .bg-border-tertiary {
          background-color: rgba(255, 255, 255, 0.06);
        }
      `}</style>
    </div>
  );
};
