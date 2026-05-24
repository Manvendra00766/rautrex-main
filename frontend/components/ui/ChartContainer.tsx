import React, { useEffect, useState } from 'react';
import { cn } from "@/lib/utils";

interface ChartContainerProps {
  children: React.ReactNode;
  height?: number;
  className?: string;
}

export function ChartContainer({ children, height = 300, className }: ChartContainerProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  
  if (!mounted) {
    return (
      <div 
        className={cn("bg-card rounded-lg flex items-center justify-center text-[14px] text-text-muted animate-pulse", className)}
        style={{ height, width: '100%' }}
      >
        Loading chart...
      </div>
    );
  }
  
  return (
    <div 
      className={cn("w-full relative", className)}
      style={{ height, minHeight: height }}
    >
      {children}
    </div>
  );
}
