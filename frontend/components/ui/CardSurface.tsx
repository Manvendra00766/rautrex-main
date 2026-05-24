import React from "react";
import { cn } from "@/lib/utils";

interface CardSurfaceProps extends React.HTMLAttributes<HTMLDivElement> {}

export function CardSurface({ className, children, ...props }: CardSurfaceProps) {
  return (
    <div 
      className={cn(
        "bg-surface border border-border shadow-sm rounded-lg p-6",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
