import React from "react";
import { cn } from "@/lib/utils";

interface PanelSurfaceProps extends React.HTMLAttributes<HTMLDivElement> {}

export function PanelSurface({ className, children, ...props }: PanelSurfaceProps) {
  return (
    <div 
      className={cn(
        "bg-card border border-border rounded-xl p-4",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
