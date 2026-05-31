"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export interface TooltipProps {
  content: string;
  children: React.ReactNode;
}

export function Tooltip({ content, children }: TooltipProps) {
  return (
    <div className="group relative flex items-center">
      {children}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50">
        <div className="bg-surface text-text-primary text-xs font-bold uppercase tracking-widest px-3 py-1.5 rounded border border-border-strong shadow-xl whitespace-nowrap">
          {content}
        </div>
      </div>
    </div>
  );
}
